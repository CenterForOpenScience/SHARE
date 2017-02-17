from hashlib import sha256
import logging

from stevedore import driver

from django.contrib.postgres.fields import JSONField
from django.core import validators
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.core.urlresolvers import reverse
from django.db import DEFAULT_DB_ALIAS
from django.db import DatabaseError
from django.db import connection
from django.db import connections
from django.db import models
from django.db.models.query_utils import DeferredAttribute
from django.db.models.query_utils import deferred_class_factory
from django.utils.deconstruct import deconstructible

from db.deletion import DATABASE_CASCADE

from share.harvest.exceptions import HarvesterConcurrencyError
from share.models.fuzzycount import FuzzyCountManager
from share.util import chunked


logger = logging.getLogger(__name__)
__all__ = ('Source', 'RawDatum', 'SourceConfig', 'Harvester', 'Transformer', 'SourceUniqueIdentifier')


class SourceIcon(models.Model):
    source = models.OneToOneField('Source', on_delete=DATABASE_CASCADE)
    image = models.BinaryField()


@deconstructible
class SourceIconStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = SourceIcon.objects.get(source__name=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        source = Source.objects.get(name=name)
        SourceIcon.objects.update_or_create(source_id=source.id, defaults={'image': content.read()})
        return name

    def delete(self, name):
        SourceIcon.objects.get(source__name=name).delete()

    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return reverse('source_icon', kwargs={'source_name': name})


def icon_name(instance, filename):
    return instance.name


class NaturalKeyManager(FuzzyCountManager):
    def __init__(self, *key_fields):
        super(NaturalKeyManager, self).__init__()
        self.key_fields = key_fields

    def get_by_natural_key(self, key):
        return self.get(**dict(zip(self.key_fields, key)))


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField(unique=True)
    home_page = models.URLField(null=True)
    icon = models.ImageField(upload_to=icon_name, storage=SourceIconStorage(), null=True)

    # TODO replace with Django permissions something something, allow multiple sources per user
    user = models.OneToOneField('ShareUser')

    objects = NaturalKeyManager('name')

    def natural_key(self):
        return (self.name,)

    def __repr__(self):
        return '<{}({}, {}, {})>'.format(self.__class__.__name__, self.pk, self.name, self.long_title)

    def __str__(self):
        return repr(self)


class SourceConfig(models.Model):
    # Previously known as the provider's app_label
    label = models.TextField(unique=True)
    version = models.TextField(default='000.000.000')

    source = models.ForeignKey('Source')
    base_url = models.URLField()
    earliest_date = models.DateField(null=True)
    rate_limit_allowance = models.PositiveIntegerField(default=5)
    rate_limit_period = models.PositiveIntegerField(default=1)

    harvester = models.ForeignKey('Harvester', null=True)
    harvester_kwargs = JSONField(null=True)

    transformer = models.ForeignKey('Transformer')
    transformer_kwargs = JSONField(null=True)

    disabled = models.BooleanField(default=False)

    objects = NaturalKeyManager('label')

    def natural_key(self):
        return (self.label,)

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
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.label)

    def __str__(self):
        return repr(self)


class Harvester(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    def natural_key(self):
        return (self.key,)

    def get_class(self):
        return driver.DriverManager('share.harvesters', self.key).driver

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.key)

    def __str__(self):
        return repr(self)


class Transformer(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    @property
    def version(self):
        return self.get_class().VERSION

    def natural_key(self):
        return (self.key,)

    def get_class(self):
        return driver.DriverManager('share.transformers', self.key).driver

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.key)

    def __str__(self):
        return repr(self)


class RawDatumManager(FuzzyCountManager):

    def link_to_log(self, log, datum_ids):
        if not datum_ids:
            return True
        logger.debug('Linking RawData to %r', log)
        with connection.cursor() as cursor:
            for chunk in chunked(datum_ids, size=500):
                if not chunk:
                    break
                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{rawdatum}", "{harvestlog}")
                    VALUES
                        {values}
                    ON CONFLICT ("{rawdatum}", "{harvestlog}") DO NOTHING;
                '''.format(
                    values=', '.join('%s' for _ in range(len(chunk))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    table=RawDatum.logs.through._meta.db_table,
                    rawdatum=RawDatum.logs.through._meta.get_field('rawdatum').column,
                    harvestlog=RawDatum.logs.through._meta.get_field('harvestlog').column,
                ), [(raw_id, log.id) for raw_id in chunk])
        return True

    def store_chunk(self, source_config, data, limit=None, db=DEFAULT_DB_ALIAS):
        # (identifier, datum)
        done = 0

        with connection.cursor() as cursor:
            for chunk in chunked(data, 500):

                if limit is not None and done + len(chunk) > limit:
                    chunk = chunk[:limit - done]

                if not chunk:
                    break

                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{identifier}", "{source_config}")
                    VALUES
                        {values}
                    ON CONFLICT
                        ("{identifier}", "{source_config}")
                    DO UPDATE SET
                        id = "{table}".id
                    RETURNING {fields}
                '''.format(
                    table=SourceUniqueIdentifier._meta.db_table,
                    identifier=SourceUniqueIdentifier._meta.get_field('identifier').column,
                    source_config=SourceUniqueIdentifier._meta.get_field('source_config').column,
                    values=', '.join('%s' for _ in range(len(chunk))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    fields=', '.join('"{}"'.format(field.column) for field in SourceUniqueIdentifier._meta.concrete_fields),
                ), [(identifier, source_config.id) for identifier, datum in chunk])

                fields = [field.attname for field in SourceUniqueIdentifier._meta.concrete_fields]
                suids = [SourceUniqueIdentifier.from_db(db, fields, row) for row in cursor.fetchall()]

                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{suid}", "{hash}", "{datum}", "{created}")
                    VALUES
                        {values}
                    ON CONFLICT
                        ("{suid}", "{hash}")
                    DO UPDATE SET
                        "{created}" = FALSE
                    RETURNING id, "{hash}", "{created}"
                '''.format(
                    table=RawDatum._meta.db_table,
                    suid=RawDatum._meta.get_field('suid').column,
                    hash=RawDatum._meta.get_field('sha256').column,
                    datum=RawDatum._meta.get_field('datum').column,
                    created=RawDatum._meta.get_field('created').column,
                    values=', '.join('%s' for _ in range(len(chunk))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                ), [
                    (suid.pk, sha256(datum).hexdigest(), datum, True)
                    for suid, (identifier, datum) in zip(suids, chunk)
                ])

                for suid, row in zip(suids, cursor.fetchall()):
                    yield MemoryFriendlyRawDatum.from_db(db, ('id', 'suid', 'sha256', 'created'), row[:1] + (suid, ) + row[1:])

                done += len(chunk)
                if limit is not None and done >= limit:
                    break

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
        return '<{}({}, {!r})>'.format(self.__class__.__name__, self.source_config_id, self.identifier)


class RawDatum(models.Model):
    datum = models.TextField()
    suid = models.ForeignKey(SourceUniqueIdentifier)
    sha256 = models.TextField(validators=[validators.MaxLengthValidator(64)])

    # Hacky field to allow us to tell if a RawDatum was updated or created in bulk inserts
    # Null default to avoid table rewrites
    created = models.NullBooleanField(null=True, default=False)

    date_modified = models.DateTimeField(auto_now=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    logs = models.ManyToManyField('HarvestLog', related_name='raw_data')

    objects = RawDatumManager()

    class Meta:
        unique_together = ('suid', 'sha256')
        verbose_name_plural = 'Raw Data'

    def __repr__(self):
        return '<{}({}, {}...)>'.format(self.__class__.__name__, self.suid_id, self.sha256[:10])

    __str__ = __repr__


# NOTE How this works changes in Django 1.10
class MemoryFriendlyRawDatum(RawDatum):

    datum = DeferredAttribute('datum', RawDatum)

    _deferred = True

    class Meta:
        proxy = True
