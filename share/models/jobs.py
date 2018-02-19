import re
import signal
import threading
import enum
import itertools
import logging
import traceback
import types
from contextlib import contextmanager

from model_utils import Choices

from django.conf import settings
from django.db import connection
from django.db import connections
from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from share.util import chunked, BaseJSONAPIMeta
from share.models.fields import DateTimeAwareJSONField


__all__ = ('HarvestJob', 'IngestJob', 'RegulatorLog')
logger = logging.getLogger(__name__)


def get_share_version():
    return settings.VERSION


class AbstractJobManager(models.Manager):
    _bulk_tmpl = '''
        INSERT INTO "{table}"
            ({insert})
        VALUES
            {{values}}
        ON CONFLICT
            ({constraint})
        DO UPDATE SET
            id = "{table}".id
        RETURNING {fields}
    '''

    _bulk_tmpl_nothing = '''
        INSERT INTO "{table}"
            ({insert})
        VALUES
            {{values}}
        ON CONFLICT ({constraint})
        DO NOTHING
        RETURNING {fields}
    '''

    def get_queryset(self):
        return LockableQuerySet(self.model, using=self._db)

    def bulk_create_or_nothing(self, fields, data, db_alias='default'):
        default_fields, default_values = self._build_defaults(fields)

        query = self._bulk_tmpl_nothing.format(
            table=self.model._meta.db_table,
            fields=', '.join('"{}"'.format(field.column) for field in self.model._meta.concrete_fields),
            insert=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in itertools.chain(fields + default_fields)),
            constraint=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in self.model._meta.unique_together[0]),
        )

        return self._bulk_query(query, default_values, data, db_alias)

    def bulk_create_or_get(self, fields, data, db_alias='default'):
        default_fields, default_values = self._build_defaults(fields)

        query = self._bulk_tmpl.format(
            table=self.model._meta.db_table,
            fields=', '.join('"{}"'.format(field.column) for field in self.model._meta.concrete_fields),
            insert=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in itertools.chain(fields + default_fields)),
            constraint=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in self.model._meta.unique_together[0]),
        )

        return self._bulk_query(query, default_values, data, db_alias)

    def bulk_get_or_create(self, objs, defaults=None, using='default'):
        if len(self.model._meta.unique_together) != 1:
            raise ValueError('Cannot determine the constraint to use for ON CONFLICT')

        if not objs:
            return []

        columns = []
        defaults = defaults or {}

        for field in self.model._meta.concrete_fields:
            if field is not self.model._meta.pk:
                columns.append(field.column)
            if field in defaults:
                continue
            if field.default is not models.NOT_PROVIDED or field.null:
                defaults[field] = field._get_default()
            elif isinstance(field, models.DateField) and (field.auto_now or field.auto_now_add):
                defaults[field] = timezone.now()

        if any(obj.pk for obj in objs):
            raise ValueError('Cannot bulk_get_or_create objects with primary keys')

        constraint = ', '.join('"{1.column}"'.format(self.model, self.model._meta.get_field(field)) for field in self.model._meta.unique_together[0])

        loaded = []
        with transaction.atomic(using):
            for chunk in chunked(objs, 500):
                if not chunk:
                    break
                loaded.extend(self.raw('''
                    INSERT INTO "{model._meta.db_table}"
                        ({columns})
                    VALUES
                        {values}
                    ON CONFLICT
                        ({constraint})
                    DO UPDATE SET
                        id = "{model._meta.db_table}".id
                    RETURNING *
                '''.format(
                    model=self.model,
                    columns=', '.join(columns),
                    constraint=constraint,
                    values=', '.join(['%s'] * len(chunk)),
                ), [
                    tuple(getattr(obj, field.attname, None) or defaults[field] for field in self.model._meta.concrete_fields[1:])
                    for obj in chunk
                ]))
        return loaded

    def _bulk_query(self, query, default_values, data, db_alias):
        fields = [field.name for field in self.model._meta.concrete_fields]

        with connection.cursor() as cursor:
            for chunk in chunked(data, 500):
                if not chunk:
                    break
                cursor.execute(query.format(
                    values=', '.join('%s' for _ in range(len(chunk))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                ), [c + default_values for c in chunk])

                for row in cursor.fetchall():
                    yield self.model.from_db(db_alias, fields, row)

    def _build_defaults(self, fields):
        default_fields, default_values = (), ()
        for field in self.model._meta.concrete_fields:
            if field.name in fields:
                continue
            if not field.null and field.default is not models.NOT_PROVIDED:
                default_fields += (field.name, )
                if isinstance(field.default, types.FunctionType):
                    default_values += (field.default(), )
                else:
                    default_values += (field.default, )
            if isinstance(field, models.DateTimeField) and (field.auto_now or field.auto_now_add):
                default_fields += (field.name, )
                default_values += (timezone.now(), )
        return default_fields, default_values


class AbstractBaseJob(models.Model):
    STATUS = Choices(
        (0, 'created', _('Enqueued')),
        (1, 'started', _('In Progress')),
        (2, 'failed', _('Failed')),
        (3, 'succeeded', _('Succeeded')),
        (4, 'rescheduled', _('Rescheduled')),
        # Used to be "defunct" which turnout to be defunct
        # Removed to avoid confusion but number has been left the same for backwards compatibility
        (6, 'forced', _('Forced')),
        (7, 'skipped', _('Skipped')),
        (8, 'retried', _('Retrying')),
        (9, 'cancelled', _('Cancelled')),
    )

    READY_STATUSES = (
        STATUS.created,
        STATUS.started,
        STATUS.rescheduled,
        STATUS.cancelled,
    )

    class SkipReasons(enum.Enum):
        duplicated = 'Previously Succeeded'
        encompassed = 'Encompassing task succeeded'
        comprised = 'Comprised of succeeded tasks'
        pointless = 'Any effects will be overwritten by another queued job'
        obsolete = 'Uses an old version of a dependency'

    task_id = models.UUIDField(null=True)
    status = models.IntegerField(db_index=True, choices=STATUS, default=STATUS.created)

    claimed = models.NullBooleanField()

    error_type = models.TextField(blank=True, null=True, db_index=True)
    error_message = models.TextField(blank=True, null=True, db_column='message')
    error_context = models.TextField(blank=True, default='', db_column='context')
    completions = models.IntegerField(default=0)

    date_started = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    share_version = models.TextField(default=get_share_version, editable=False)

    objects = AbstractJobManager()

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        abstract = True
        ordering = ('-date_modified', )

    def start(self, claim=False):
        # TODO double check existing values to make sure everything lines up.
        stamp = timezone.now()
        logger.debug('Setting %r to started at %r', self, stamp)
        self.status = self.STATUS.started
        self.claimed = claim
        self.date_started = stamp
        self.save(update_fields=('status', 'claimed', 'date_started', 'date_modified'))

        return True

    def fail(self, exception):
        logger.debug('Setting %r to failed due to %r', self, exception)

        self.error_message = exception
        if isinstance(exception, Exception):
            self.error_type = type(exception).__name__
            tb = traceback.TracebackException.from_exception(exception)
            self.error_context = '\n'.join(tb.format(chain=True))
        else:
            self.error_type = None
            self.error_context = ''

        self.status = self.STATUS.failed
        self.claimed = False
        self.save(update_fields=('status', 'error_type', 'error_message', 'error_context', 'claimed', 'date_modified'))

        return True

    def succeed(self):
        self.error_type = None
        self.error_message = None
        self.error_context = ''
        self.claimed = False
        self.completions += 1
        self.status = self.STATUS.succeeded
        logger.debug('Setting %r to succeeded with %d completions', self, self.completions)
        self.save(update_fields=('status', 'error_type', 'error_message', 'error_context', 'completions', 'claimed', 'date_modified'))

        return True

    def reschedule(self, claim=False):
        self.status = self.STATUS.rescheduled
        self.claimed = claim
        self.save(update_fields=('status', 'claimed', 'date_modified'))

        return True

    def forced(self, exception):
        logger.debug('Setting %r to forced with error_context %r', self, exception)

        self.error_message = exception
        if isinstance(exception, Exception):
            self.error_type = type(exception).__name__
            tb = traceback.TracebackException.from_exception(exception)
            self.error_context = '\n'.join(tb.format(chain=True))
        else:
            self.error_type = None
            self.error_context = ''

        self.status = self.STATUS.forced
        self.claimed = False
        self.save(update_fields=('status', 'error_type', 'error_message', 'error_context', 'claimed', 'date_modified'))

        return True

    def skip(self, reason):
        logger.debug('Setting %r to skipped with context %r', self, reason)

        self.completions += 1
        self.error_context = reason.value
        self.status = self.STATUS.skipped
        self.claimed = False
        self.save(update_fields=('status', 'error_context', 'completions', 'claimed', 'date_modified'))

        return True

    def cancel(self):
        logger.debug('Setting %r to cancelled', self)

        self.status = self.STATUS.cancelled
        self.claimed = False
        self.save(update_fields=('status', 'claimed', 'date_modified'))

        return True

    @contextmanager
    def handle(self):
        # Flush any pending changes. Any updates
        # beyond here will be field specific
        self.save()

        is_main_thread = threading.current_thread() == threading.main_thread()

        if is_main_thread:
            # Protect ourselves from SIGTERM
            def on_sigterm(sig, frame):
                self.cancel()
            prev_handler = signal.signal(signal.SIGTERM, on_sigterm)

        self.start()
        try:
            yield
        except Exception as e:
            self.fail(e)
            raise
        else:
            # If the handler didn't handle setting a status, assume success
            if self.status == self.STATUS.started:
                self.succeed()
        finally:
            if is_main_thread:
                # Detach from SIGTERM, resetting the previous handle
                signal.signal(signal.SIGTERM, prev_handler)

    def current_versions(self):
        raise NotImplementedError

    def update_versions(self):
        """Update version fields to the values from self.current_versions

        Return True if successful, else False.
        """
        current_versions = self.current_versions()
        if all(getattr(self, f) == v for f, v in current_versions.items()):
            # No updates required
            return True

        if self.completions > 0:
            logger.warning('%r is outdated but has previously completed, skipping...', self)
            return False

        try:
            with transaction.atomic():
                for f, v in current_versions.items():
                    setattr(self, f, v)
                self.save()
            logger.warning('%r has been updated to the versions: %s', self, current_versions)
            return True
        except IntegrityError:
            logger.warning('A newer version of %r already exists, skipping...', self)
            return False

    def __repr__(self):
        return '<{} {} ({})>'.format(self.__class__.__name__, self.id, self.STATUS[self.status])


class PGLock(models.Model):
    """A wrapper around Postgres' pg_locks system table.
    manged = False stops this model from doing anything strange to the table
    but allows us to safely query this table.
    """

    pid = models.IntegerField(primary_key=True)
    locktype = models.TextField()
    objid = models.IntegerField()
    classid = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'pg_locks'


class LockableQuerySet(models.QuerySet):
    LOCK_ACQUIRED = re.sub('\s\s+', ' ', '''
        pg_try_advisory_lock(%s::REGCLASS::INTEGER, "{0.model._meta.db_table}"."{0.column}")
    ''').strip()

    def unlocked(self, relation):
        """Filter out any rows that have an advisory lock on the related field.

        Args:
            relation: (str): The related object to check for an advisory lock on.

        """
        field = self.model._meta.get_field(relation)

        if not field.is_relation:
            raise ValueError('Field "{}" of "{}" is not a relation'.format(relation, self.model))

        return self.select_related(relation).annotate(
            is_locked=models.Exists(PGLock.objects.filter(
                locktype='advisory',
                objid=models.OuterRef(field.column),
                classid=RawSQL('%s::REGCLASS::INTEGER', [field.related_model._meta.db_table])
            ))
        ).exclude(is_locked=True)

    @contextmanager
    def lock_first(self, relation):
        item = None
        field = self.model._meta.get_field(relation)

        if not field.is_relation:
            raise ValueError('Field "{}" of "{}" is not a relation'.format(relation, self.model))

        try:
            item = type(self)(self.model, using=self.db).select_related(relation).filter(
                id__in=self.values('id')[:1]
            ).annotate(
                lock_acquired=RawSQL(self.LOCK_ACQUIRED.format(field), [field.related_model._meta.db_table])
            ).first()

            yield item
        finally:
            if item and item.lock_acquired:
                with connections[self.db].cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s::REGCLASS::INTEGER, %s)', [field.related_model._meta.db_table, getattr(item, field.attname)])

    def acquire_lock(self, relation):
        """Attempts to acquire an advisory lock for ALL rows returned by this queryset.

        Note:
            Locks not take effect until the queryset is evaluated.
            It will, however, affect everything if you use .all().

        Args:
            relation: (str): The related object to attempt to acquire an advisory lock on.

        """
        field = self.model._meta.get_field(relation)

        if not field.is_relation:
            raise ValueError('Field "{}" of "{}" is not a relation'.format(relation, self.model))

        return self.select_related(relation).annotate(
            lock_acquired=RawSQL(self.LOCK_ACQUIRED.format(field), [field.related_model._meta.db_table])
        )


class HarvestJob(AbstractBaseJob):
    # May want to look into using DateRange in the future
    end_date = models.DateField(db_index=True)
    start_date = models.DateField(db_index=True)

    source_config = models.ForeignKey('SourceConfig', editable=False, related_name='harvest_jobs', on_delete=models.CASCADE)
    source_config_version = models.PositiveIntegerField()
    harvester_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ('source_config', 'start_date', 'end_date', 'harvester_version', 'source_config_version', )
        # Used to be inaccurately named
        db_table = 'share_harvestlog'

    def current_versions(self):
        return {
            'source_config_version': self.source_config.version,
            'harvester_version': self.source_config.harvester.version,
        }

    def __repr__(self):
        return '<{type}({id}, {status}, {source}, {start_date}, {end_date})>'.format(
            type=type(self).__name__,
            id=self.id,
            source=self.source_config.label,
            status=self.STATUS[self.status],
            end_date=self.end_date.isoformat(),
            start_date=self.start_date.isoformat(),
        )


class IngestJob(AbstractBaseJob):
    raw = models.ForeignKey('RawDatum', editable=False, related_name='ingest_jobs', on_delete=models.CASCADE)
    suid = models.ForeignKey('SourceUniqueIdentifier', editable=False, related_name='ingest_jobs', on_delete=models.CASCADE)
    source_config = models.ForeignKey('SourceConfig', editable=False, related_name='ingest_jobs', on_delete=models.CASCADE)

    source_config_version = models.PositiveIntegerField()
    transformer_version = models.PositiveIntegerField()
    regulator_version = models.PositiveIntegerField()

    transformed_datum = DateTimeAwareJSONField(null=True)
    regulated_datum = DateTimeAwareJSONField(null=True)

    ingested_normalized_data = models.ManyToManyField('NormalizedData', related_name='ingest_jobs')

    retries = models.IntegerField(null=True)

    @classmethod
    def schedule(cls, raw, superfluous=False, claim=False):
        # TODO does this belong here?
        from share.regulate import Regulator
        job, _ = cls.objects.get_or_create(
            raw=raw,
            suid=raw.suid,
            source_config=raw.suid.source_config,
            source_config_version=raw.suid.source_config.version,
            transformer_version=raw.suid.source_config.transformer.version,
            regulator_version=Regulator.VERSION,
            claimed=claim,
        )
        if superfluous and job.status not in cls.READY_STATUSES:
            job.status = cls.STATUS.created
            job.save()
        return job

    class Meta:
        unique_together = ('raw', 'source_config_version', 'transformer_version', 'regulator_version')

    def current_versions(self):
        # TODO does this belong here?
        from share.regulate import Regulator
        return {
            'source_config_version': self.source_config.version,
            'transformer_version': self.source_config.transformer.version,
            'regulator_version': Regulator.VERSION,
        }

    def log_graph(self, field_name, graph):
        setattr(self, field_name, graph.to_jsonld())
        self.save(update_fields=(field_name, 'date_modified'))

    def __repr__(self):
        return '<{type}({id}, {status}, {source}, {suid})>'.format(
            type=type(self).__name__,
            id=self.id,
            status=self.STATUS[self.status],
            source=self.source_config.label,
            suid=self.suid.identifier,
        )


class RegulatorLog(models.Model):
    description = models.TextField()
    node_id = models.TextField(null=True)
    rejected = models.BooleanField()

    ingest_job = models.ForeignKey(IngestJob, related_name='regulator_logs', editable=False, on_delete=models.CASCADE)
