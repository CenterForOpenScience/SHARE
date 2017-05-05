import re
import signal
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
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from share.util import chunked
from share.harvest.exceptions import HarvesterConcurrencyError


__all__ = ('HarvestLog', )
logger = logging.getLogger(__name__)


def get_share_version():
    return settings.VERSION


class AbstractLogManager(models.Manager):
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


class AbstractBaseLog(models.Model):
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
        encompassed = 'Encompassing task succeeded',
        comprised = 'Comprised of succeeded tasks',

    task_id = models.UUIDField(null=True)
    status = models.IntegerField(db_index=True, choices=STATUS, default=STATUS.created)

    context = models.TextField(blank=True, default='')
    completions = models.IntegerField(default=0)

    date_started = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    source_config = models.ForeignKey('SourceConfig', editable=False, related_name='harvest_logs', on_delete=models.CASCADE)

    share_version = models.TextField(default=get_share_version, editable=False)
    source_config_version = models.PositiveIntegerField()

    objects = AbstractLogManager()

    class Meta:
        abstract = True
        ordering = ('-date_modified', )

    def start(self):
        # TODO double check existing values to make sure everything lines up.
        stamp = timezone.now()
        logger.debug('Setting %r to started at %r', self, stamp)
        self.status = self.STATUS.started
        self.date_started = stamp
        self.save(update_fields=('status', 'date_started', 'date_modified'))

        return True

    def fail(self, exception):
        logger.debug('Setting %r to failed due to %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = self.STATUS.failed
        self.context = exception
        self.save(update_fields=('status', 'context', 'date_modified'))

        return True

    def succeed(self):
        self.context = ''
        self.completions += 1
        self.status = self.STATUS.succeeded
        logger.debug('Setting %r to succeeded with %d completions', self, self.completions)
        self.save(update_fields=('context', 'completions', 'status', 'date_modified'))

        return True

    def reschedule(self):
        self.status = self.STATUS.rescheduled
        self.save(update_fields=('status', 'date_modified'))

        return True

    def forced(self, exception):
        logger.debug('Setting %r to forced with context %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = self.STATUS.forced
        self.context = exception
        self.save(update_fields=('status', 'context', 'date_modified'))

        return True

    def skip(self, reason):
        logger.debug('Setting %r to skipped with context %r', self, reason)

        self.completions += 1
        self.context = reason.value
        self.status = self.STATUS.skipped
        self.save(update_fields=('status', 'context', 'completions', 'date_modified'))

        return True

    def cancel(self):
        logger.debug('Setting %r to cancelled', self)

        self.status = self.STATUS.cancelled
        self.save(update_fields=('status', 'date_modified'))

        return True

    @contextmanager
    def handle(self):
        error = None
        # Flush any pending changes. Any updates
        # beyond here will be field specific
        self.save()

        # Protect ourselves from SIGKILL
        def on_sigkill(sig, frame):
            self.cancel()
        prev_handler = signal.signal(signal.SIGTERM, on_sigkill)

        self.start()
        try:
            yield
        except HarvesterConcurrencyError as e:
            error = e
            self.reschedule()
        except Exception as e:
            error = e
            self.fail(error)
        else:
            self.succeed()
        finally:
            # Detach from SIGKILL, resetting the previous handle
            signal.signal(signal.SIGTERM, prev_handler)

            # Reraise the error if we caught one
            if error:
                raise error


class LockableQuerySet(models.QuerySet):
    LOCK_ACQUIRED = re.sub('\s\s+', ' ', '''
        pg_try_advisory_lock(%s::REGCLASS::INTEGER, "{0.model._meta.db_table}"."{0.column}")
    ''').strip()

    IS_LOCKED = re.sub('\s\s+', ' ', '''
        EXISTS(
            SELECT * FROM pg_locks
            WHERE locktype = 'advisory'
            AND objid = {0._meta.db_table}.{0._meta.pk.column}
            AND classid = %s::REGCLASS::INTEGER
            AND locktype = 'advisory'
        )
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
            is_locked=RawSQL(self.IS_LOCKED.format(field.related_model), [field.related_model._meta.db_table])
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


class HarvestLogManager(AbstractLogManager):
    def get_queryset(self):
        return LockableQuerySet(self.model, using=self._db)


class HarvestLog(AbstractBaseLog):
    # May want to look into using DateRange in the future
    end_date = models.DateField(db_index=True)
    start_date = models.DateField(db_index=True)
    harvester_version = models.PositiveIntegerField()

    objects = HarvestLogManager()

    class Meta:
        unique_together = ('source_config', 'start_date', 'end_date', 'harvester_version', 'source_config_version', )

    def handle(self, harvester_version):
        self.harvester_version = harvester_version
        return super().handle()

    def __repr__(self):
        return '<{type}({id}, {status}, {source}, {start_date}, {end_date})>'.format(
            type=type(self).__name__,
            id=self.id,
            source=self.source_config.label,
            status=self.STATUS[self.status],
            end_date=self.end_date.isoformat(),
            start_date=self.start_date.isoformat(),
        )
