import itertools
import logging
import traceback

from model_utils import Choices

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import connection
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from share.util import chunked


logger = logging.getLogger(__name__)
__all__ = ('HarvestLog', 'IngestLog')

VersionValidator = RegexValidator('^\d\d\d\.\d\d\d\.\d\d\d$')


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

    def bulk_create_or_get(self, fields, data, db_alias='default'):

        default_fields, default_values = (), ()
        for field in self.model._meta.concrete_fields:
            if field.name in fields:
                continue
            if not field.null and field.default is not models.NOT_PROVIDED:
                default_fields += (field.name, )
                default_values += (field.default, )
            if isinstance(field, models.DateTimeField) and (field.auto_now or field.auto_now_add):
                default_fields += (field.name, )
                default_values += (timezone.now(), )

        query = self._bulk_tmpl.format(
            table=self.model._meta.db_table,
            fields=', '.join('"{}"'.format(field.column) for field in self.model._meta.concrete_fields),
            insert=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in itertools.chain(fields + default_fields)),
            constraint=', '.join('"{}"'.format(self.model._meta.get_field(field).column) for field in self.model._meta.unique_together[0]),
        )

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


class AbstractBaseLog(models.Model):
    STATUS = Choices(
        (0, 'created', _('Enqueued')),
        (1, 'started', _('In Progress')),
        (2, 'failed', _('Failed')),
        (3, 'succeeded', _('Succeeded')),
        (4, 'rescheduled', _('Rescheduled')),
        (5, 'defunct', _('Defunct')),
        (5, 'forced', _('Forced')),
    )

    task_id = models.UUIDField(null=True)
    status = models.IntegerField(db_index=True, choices=STATUS, default=STATUS.created)

    error = models.TextField(blank=True, default='')
    completions = models.IntegerField(default=0)

    date_started = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True, editable=False)

    source_config = models.ForeignKey('SourceConfig')

    share_version = models.TextField(default=settings.VERSION)
    source_config_version = models.PositiveIntegerField()

    objects = AbstractLogManager()

    class Meta:
        abstract = True

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
        self.error = exception

        if save:
            self.save()
        return True

    def succeed(self, save=True):
        self.error = ''
        self.completions += 1
        self.status = self.STATUS.succeeded
        logger.debug('Setting %r to succeeded with %d completions', self, self.completions)
        if save:
            self.save()
        return True

    def reschedule(self, exception, save=True):
        self.status = self.STATUS.rescheduled
        if save:
            self.save()
        return True

    def forced(self, exception, save=True):
        logger.debug('Setting %r to forced with error %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = self.STATUS.forced
        self.error = exception

        if save:
            self.save()
        return True


class HarvestLog(AbstractBaseLog):
    end_date = models.DateTimeField()
    start_date = models.DateTimeField()
    harvester_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ('source_config', 'start_date', 'end_date', 'harvester_version', 'source_config_version', )


class IngestLog(AbstractBaseLog):
    raw_datum = models.ForeignKey('RawDatum')

    regulator_version = models.TextField(blank=True, default='', validators=[VersionValidator])
    transformer_version = models.TextField(validators=[VersionValidator])
    consolidator_version = models.TextField(blank=True, default='', validators=[VersionValidator])

    class Meta:
        unique_together = ('raw_datum', 'transformer_version')
