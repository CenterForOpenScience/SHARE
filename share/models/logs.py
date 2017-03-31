import enum
import itertools
import logging
import traceback
import types

from model_utils import Choices

from django.conf import settings
from django.db import connection
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from share.util import chunked


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

    source_config = models.ForeignKey('SourceConfig', editable=False, related_name='harvest_logs')

    share_version = models.TextField(default=get_share_version, editable=False)
    source_config_version = models.PositiveIntegerField()

    objects = AbstractLogManager()

    class Meta:
        abstract = True
        ordering = ('-date_modified', )

    def start(self, save=True):
        # TODO double check existing values to make sure everything lines up.
        stamp = timezone.now()
        logger.debug('Setting %r to started at %r', self, stamp)
        self.status = self.STATUS.started
        self.date_started = stamp
        if save:
            self.save()
        return True

    def fail(self, exception, save=True):
        logger.debug('Setting %r to failed due to %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = self.STATUS.failed
        self.context = exception

        if save:
            self.save()
        return True

    def succeed(self, save=True):
        self.context = ''
        self.completions += 1
        self.status = self.STATUS.succeeded
        logger.debug('Setting %r to succeeded with %d completions', self, self.completions)
        if save:
            self.save()
        return True

    def reschedule(self, save=True):
        self.status = self.STATUS.rescheduled
        if save:
            self.save()
        return True

    def forced(self, exception, save=True):
        logger.debug('Setting %r to forced with context %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = self.STATUS.forced
        self.context = exception

        if save:
            self.save()
        return True

    def skip(self, reason, save=True):
        logger.debug('Setting %r to skipped with context %r', self, reason)

        self.completions += 1
        self.context = reason.value
        self.status = self.STATUS.skipped

        if save:
            self.save()
        return True


class HarvestLog(AbstractBaseLog):
    # May want to look into using DateRange in the future
    end_date = models.DateField(db_index=True)
    start_date = models.DateField(db_index=True)
    harvester_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ('source_config', 'start_date', 'end_date', 'harvester_version', 'source_config_version', )

    def spawn_task(self, ingest=True, force=False, limit=None, superfluous=False, ignore_disabled=False, async=True):
        from share.tasks import HarvesterTask
        # TODO Move most if not all of the logic for task argument massaging here.
        # It's bad to have two places already but this is required to backharvest a source without timing out on uwsgi
        task = HarvesterTask()

        targs = (1, self.source_config.label)
        tkwargs = {
            'end': self.end_date.isoformat(),
            'start': self.start_date.isoformat(),
            'ingest': ingest,
            'limit': limit,
            'force': force,
            'superfluous': superfluous
        }

        if async:
            return HarvesterTask.mro()[1].apply_async(task, targs, tkwargs, task_id=self.task_id)
        return HarvesterTask.mro()[1].apply(task, targs, tkwargs, task_id=self.task_id, throw=True)

    def __repr__(self):
        return '<{type}({id}, {status}, {source}, {start_date}, {end_date})>'.format(
            type=type(self).__name__,
            id=self.id,
            source=self.source_config.label,
            status=self.STATUS[self.status],
            end_date=self.end_date.isoformat(),
            start_date=self.start_date.isoformat(),
        )
