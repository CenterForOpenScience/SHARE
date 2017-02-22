from hashlib import sha256
import datetime
import logging
import traceback

from model_utils import Choices

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core import validators
from django.core.files.storage import Storage
from django.db import DatabaseError
from django.db import connection
from django.db import connections
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _

from db.deletion import DATABASE_CASCADE

from share.harvest.exceptions import HarvesterConcurrencyError
from share.models.fuzzycount import FuzzyCountManager
from share.util import chunked


logger = logging.getLogger(__name__)
__all__ = ('Source', 'HarvestLog', 'RawDatum', 'SourceConfig', 'Harvester', 'Transformer', 'SourceUniqueIdentifier')


class SourceIcon(models.Model):
    source = models.OneToOneField('Source', on_delete=DATABASE_CASCADE)
    image = models.BinaryField()


@deconstructible
class SourceIconStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = SourceIcon.objects.get(source_name=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        source = Source.objects.get(name=name)
        SourceIcon.objects.update_or_create(source_id=source.id, defaults={'image': content.read()})
        return name

    def delete(self, name):
        SourceIcon.objects.get(source_name=name).delete()

    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return reverse('source_icon', kwargs={'source_name': name})


def icon_name(instance, filename):
    return instance.name


class NaturalKeyManager(FuzzyCountManager):
    def __init__(self, key_field):
        super(NaturalKeyManager, self).__init__()
        self.key_field = key_field

    def get_by_natural_key(self, key):
        return self.get(**{self.key_field: key})


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField(unique=True)
    home_page = models.URLField(null=True)
    icon = models.ImageField(upload_to=icon_name, storage=SourceIconStorage(), null=True)

    # TODO replace with Django permissions something something
    user = models.ForeignKey('ShareUser')

    objects = NaturalKeyManager('name')

    def natural_key(self):
        return self.name

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.name)


class SourceConfig(models.Model):
    # Previously known as the provider's app_label
    label = models.TextField(unique=True)
    version = models.TextField(default='000.000.000')

    source = models.ForeignKey('Source')
    base_url = models.URLField()
    earliest_date = models.DateField(null=True)
    rate_limit_allowance = models.PositiveIntegerField(default=5)
    rate_limit_period = models.PositiveIntegerField(default=1)

    harvester = models.ForeignKey('Harvester')
    harvester_kwargs = JSONField(null=True)

    transformer = models.ForeignKey('Transformer')
    transformer_kwargs = JSONField(null=True)

    disabled = models.BooleanField(default=False)

    def get_harvester(self):
        return self.harvester.get_class()(self, **(self.harvester_kwargs or {}))

    def get_transformer(self):
        return self.transformer.get_class()(self, **(self.transformer_kwargs or {}))

    def acquire_lock(self, using='locking'):
        # NOTE: Must be in transaction
        logger.debug('Attempting to lock %r', self)
        try:
            with connections[using].cursor() as cursor:
                cursor.execute('''
                    SELECT "id"
                    FROM "{}"
                    WHERE id = %s
                    FOR NO KEY UPDATE NOWAIT;
                '''.format(self._meta.db_table), (self.id,))
        except DatabaseError:
            logger.warning('Lock failed; another task is already harvesting %r.', self)
            raise HarvesterConcurrencyError('Unable to lock {!r}'.format(self))
        else:
            logger.debug('Lock acquired on %r', self)

    def __repr__(self):
        return '<{}({}, {!r})>'.format(self.__class__.__name__, self.label, self.source)


class Harvester(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    @property
    def version(self):
        return self.get_class().VERSION

    def natural_key(self):
        return self.key

    def get_class(self):
        from share.harvest import BaseHarvester
        return BaseHarvester.registry[self.key]


class Transformer(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    @property
    def version(self):
        return self.get_class().VERSION

    def natural_key(self):
        return self.key

    def get_class(self):
        from share.transform import BaseTransformer
        return BaseTransformer.registry[self.key]


class HarvestLog(models.Model):
    STATUS = Choices(
        (0, 'created', _('Enqueued')),
        (1, 'started', _('In Progress')),
        (2, 'failed', _('Failed')),
        (2, 'succeeded', _('Succeeded')),
        (2, 'rescheduled', _('Rescheduled')),
    )

    task_id = models.UUIDField(null=True)

    status = models.IntegerField(db_index=True, choices=STATUS, default=STATUS.created)
    error = models.TextField(blank=True)
    completions = models.IntegerField(default=0)

    end_date = models.DateTimeField()
    start_date = models.DateTimeField()

    date_started = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True, editable=False)

    source_config = models.ForeignKey('SourceConfig')

    share_version = models.TextField(default=settings.VERSION)
    harvester_version = models.TextField()
    source_config_version = models.TextField()

    class Meta:
        unique_together = ('source_config', 'start_date', 'end_date', 'harvester_version', 'source_config_version', )

    def start(self, save=True):
        # TODO double check existing values to make sure everything lines up.
        stamp = datetime.datetime.utcnow()  # TODO check for timezone
        logger.debug('Setting %r to started at %r', self, stamp)
        self.status = HarvestLog.STATUS.started
        self.date_started = stamp
        if save:
            self.save()
        return True

    def fail(self, exception, save=True):
        logger.debug('Setting %r to failed due to %r', self, exception)

        if not isinstance(exception, str):
            tb = traceback.TracebackException.from_exception(exception)
            exception = '\n'.join(tb.format(chain=True))

        self.status = HarvestLog.STATUS.failed
        self.error = exception

        if save:
            self.save()
        return True

    def succeed(self, save=True):
        self.completions += 1
        self.status = HarvestLog.STATUS.succeeded
        logger.debug('Setting %r to succeeded with %d completions', self, self.completions)
        if save:
            self.save()
        return True

    def reschedule(self, exception, save=True):
        self.status = HarvestLog.STATUS.rescheduled
        if save:
            self.save()
        return True


class RawDatumManager(FuzzyCountManager):

    def link_to_log(self, log, datum_ids):
        if not datum_ids:
            return True
        logger.debug('Linking RawData to %r', log)
        with connection.cursor() as cursor:
            for chunk in chunked(datum_ids, size=500):
                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{rawdatum}", "{harvestlog}")
                    VALUES
                        {values}
                    ON CONFLICT ("{rawdatum}", "{harvestlog}") DO NOTHING;
                '''.format(
                    values=', '.join(('%s', ) * len(chunk)),  # Nast hack. Fix when psycopg2 2.7 is released with execute_values
                    table=RawDatum.logs.through._meta.db_table,
                    rawdatum=RawDatum.logs.through._meta.get_field('rawdatum').column,
                    harvestlog=RawDatum.logs.through._meta.get_field('harvestlog').column,
                ), [(raw_id, log.id) for raw_id in chunk])
        return True

    # def store_chunk(self, *data):
    #     # (identifier, datum, config)
    #     with connection.cursor() as cursor:
    #         for chunk in chunked(data, 500):
    #             suid_pks = cursor.execute('''
    #                 INSERT INTO "{table}"
    #                     ("{identifier}", "{source_config}")
    #                 VALUES
    #                     {values}
    #                 ON CONFLICT
    #                     ("{identifier}", "{source_config}")
    #                 DO UPDATE SET
    #                     id = "{table}".id
    #                 RETURNING id
    #                 ;
    #             '''.format(
    #             ))

    #             suid_pks = cursor.execute('''
    #                 INSERT INTO "{table}"
    #                     ("{identifier}", "{source_config}")
    #                 VALUES
    #                     {values}
    #                 ON CONFLICT
    #                     ("{identifier}", "{source_config}")
    #                 DO UPDATE SET
    #                     id = "{table}".id
    #                 RETURNING id
    #                 ;
    #             '''.format(
    #             ))

    def store_data(self, identifier, datum, config):
        suid, _ = SourceUniqueIdentifier.objects.get_or_create(identifier=identifier, source_config=config)
        rd, created = self.get_or_create(suid=suid, datum=datum, sha256=sha256(datum).hexdigest())

        if created:
            logger.debug('New RawDatum for %r', suid)
        else:
            logger.debug('Found existing RawDatum for %r', suid)

        return rd, created


class SourceUniqueIdentifier(models.Model):
    identifier = models.TextField()
    source_config = models.ForeignKey('SourceConfig')

    class Meta:
        unique_together = ('identifier', 'source_config')

    def __str__(self):
        return '{} {}'.format(self.source_config_id, self.identifier)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.source_config_id, self.identifier)


class RawDatum(models.Model):
    datum = models.TextField()
    suid = models.ForeignKey(SourceUniqueIdentifier)
    sha256 = models.TextField(validators=[validators.MaxLengthValidator(64)])

    # Hacky field to allow us to tell if a RawDatum was updated or created in bulk inserts
    created = models.BooleanField(default=False)

    logs = models.ManyToManyField('HarvestLog', related_name='raw_data')

    objects = RawDatumManager()

    class Meta:
        unique_together = ('suid', 'sha256')
        verbose_name_plural = 'Raw Data'

    def __repr__(self):
        return '<{}({!r}, {})>'.format(self.__class__.__name__, self.suid, self.sha256)

    __str__ = __repr__
