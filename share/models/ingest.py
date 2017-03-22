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
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from share.harvest.exceptions import HarvesterConcurrencyError
from share.models.fuzzycount import FuzzyCountManager
from share.util import chunked


logger = logging.getLogger(__name__)
__all__ = ('Source', 'RawDatum', 'SourceConfig', 'Harvester', 'Transformer', 'SourceUniqueIdentifier')


class SourceIcon(models.Model):
    source_name = models.TextField(unique=True)
    image = models.BinaryField()


@deconstructible
class SourceIconStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = SourceIcon.objects.get(source_name=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        SourceIcon.objects.update_or_create(source_name=name, defaults={'image': content.read()})
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
    version = models.PositiveIntegerField(default=1)

    source = models.ForeignKey('Source')
    base_url = models.URLField(null=True)
    earliest_date = models.DateField(null=True)
    rate_limit_allowance = models.PositiveIntegerField(default=5)
    rate_limit_period = models.PositiveIntegerField(default=1)

    # Allow null for push sources
    harvester = models.ForeignKey('Harvester', null=True)
    harvester_kwargs = JSONField(null=True)

    # Allow null for push sources
    # TODO put pushed data through a transformer, add a JSONLDTransformer or something for backward compatibility
    transformer = models.ForeignKey('Transformer', null=True)
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

    def find_missing_dates(self):
        from share.models import HarvestLog
        # Thank god for stack overflow
        # http://stackoverflow.com/questions/9604400/sql-query-to-show-gaps-between-multiple-date-ranges
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT "{end_date}", "{start_date}"
                FROM (
                    SELECT DISTINCT "{start_date}", ROW_NUMBER() OVER (ORDER BY "{start_date}") RN
                    FROM "{harvestlog}" T1
                    WHERE T1."{source_config}" = %(source_config_id)s
                    AND T1."{harvester_version}" = %(harvester_version)s
                    AND NOT EXISTS (
                        SELECT * FROM "{harvestlog}" T2
                        WHERE T2."{source_config}" = %(source_config_id)s
                        AND T2."{harvester_version}" = %(harvester_version)s
                        AND T1."{start_date}" > T2."{start_date}"
                        AND T1."{start_date}" < T2."{end_date}")
                ) T1 JOIN (
                    SELECT DISTINCT "{end_date}", ROW_NUMBER() OVER (ORDER BY "{end_date}") RN
                    FROM "{harvestlog}" T1
                    WHERE T1."{source_config}" = %(source_config_id)s
                    AND T1."{harvester_version}" = %(harvester_version)s
                    AND NOT EXISTS (
                        SELECT * FROM "{harvestlog}" T2
                        WHERE T2."{source_config}" = %(source_config_id)s
                        AND T2."{harvester_version}" = %(harvester_version)s
                        AND T1."{end_date}" > T2."{start_date}"
                        AND T1."{end_date}" < T2."{end_date}")
                ) T2 ON T1.RN - 1 = T2.RN
                WHERE "{end_date}" < "{start_date}"
            '''.format(
                harvestlog=HarvestLog._meta.db_table,
                end_date=HarvestLog._meta.get_field('end_date').column,
                start_date=HarvestLog._meta.get_field('start_date').column,
                source_config=HarvestLog._meta.get_field('source_config').column,
                harvester_version=HarvestLog._meta.get_field('harvester_version').column,
            ), {
                'source_config_id': self.id,
                'harvester_version': self.get_harvester().VERSION,
            })
            return cursor.fetchall()

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.label)

    def __str__(self):
        return '{}: {}'.format(self.source.long_title, self.label)


class Harvester(models.Model):
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
        """Store a large amount of data for a single source_config.

        Data MUST be a utf-8 encoded string (Just a str type).
        Take special care to make sure you aren't destroying data by mis-encoding it.

        Args:
            source_config (SourceConfig):
            data Generator[(str, str)]: (identifier, datum)

        Returns:
            Generator[MemoryFriendlyRawDatum]
        """
        done = 0
        now = timezone.now()

        with connection.cursor() as cursor:
            for chunk in chunked(data, 500):

                if limit is not None and done + len(chunk) > limit:
                    chunk = chunk[:limit - done]

                if not chunk:
                    break

                identifiers = list({(identifier, source_config.id) for identifier, datum in chunk})

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
                    values=', '.join('%s' for _ in range(len(identifiers))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    fields=', '.join('"{}"'.format(field.column) for field in SourceUniqueIdentifier._meta.concrete_fields),
                ), identifiers)

                suids = {}
                fields = [field.attname for field in SourceUniqueIdentifier._meta.concrete_fields]
                for row in cursor.fetchall():
                    suid = SourceUniqueIdentifier.from_db(db, fields, row)
                    suids[suid.pk] = suid
                    suids[suid.identifier] = suid

                raw_data = {}
                for identifier, datum in chunk:
                    hash_ = sha256(datum.encode('utf-8')).hexdigest()
                    raw_data[identifier, hash_] = (suids[identifier].pk, hash_, datum, now, now)

                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{suid}", "{hash}", "{datum}", "{date_created}", "{date_modified}")
                    VALUES
                        {values}
                    ON CONFLICT
                        ("{suid}", "{hash}")
                    DO UPDATE SET
                        "{date_modified}" = %s
                    RETURNING id, "{suid}", "{hash}", "{date_created}", "{date_modified}"
                '''.format(
                    table=RawDatum._meta.db_table,
                    suid=RawDatum._meta.get_field('suid').column,
                    hash=RawDatum._meta.get_field('sha256').column,
                    datum=RawDatum._meta.get_field('datum').column,
                    date_created=RawDatum._meta.get_field('date_created').column,
                    date_modified=RawDatum._meta.get_field('date_modified').column,
                    values=', '.join('%s' for _ in range(len(raw_data))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                ), list(raw_data.values()) + [now])

                for row in cursor.fetchall():
                    yield MemoryFriendlyRawDatum.from_db(db, ('id', 'suid', 'sha256', 'date_created', 'date_modified'), row[:1] + (suids[row[1]], ) + row[2:])

                done += len(raw_data)
                if limit is not None and done >= limit:
                    break

    def store_data(self, identifier, datum, config):
        """
        """
        (rd, ) = self.store_chunk(config, [(identifier, datum)])

        if rd.created:
            logger.debug('New %r', rd)
        else:
            logger.debug('Found existing %r', rd)

        return rd


# class SUIDManager(FuzzyCountManager):
#     _bulk_tmpl = '''
#         INSERT INTO "{table}"
#             ("{identifier}", "{source_config}")
#         VALUES
#             {values}
#         ON CONFLICT
#             ("{identifier}", "{source_config}")
#         DO UPDATE SET
#             id = "{table}".id
#         RETURNING {fields}
#     '''

#     def bulk_get_or_create(self, data, chunk_size=500):
#         pass


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

    # The sha256 of the datum
    sha256 = models.TextField(validators=[validators.MaxLengthValidator(64)])

    # Does this datum contain a full record or just a sparse update
    # partial = models.NullBooleanField(null=True, default=False)

    date_modified = models.DateTimeField(auto_now=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    logs = models.ManyToManyField('HarvestLog', related_name='raw_data')

    objects = RawDatumManager()

    @property
    def created(self):
        return self.date_modified == self.date_created

    class Meta:
        unique_together = ('suid', 'sha256')
        verbose_name_plural = 'Raw Data'

    class JSONAPIMeta:
        resource_name = 'RawData'

    def __repr__(self):
        return '<{}({}, {}...)>'.format(self.__class__.__name__, self.suid_id, self.sha256[:10])

    __str__ = __repr__


# NOTE How this works changes in Django 1.10
class MemoryFriendlyRawDatum(RawDatum):

    datum = DeferredAttribute('datum', RawDatum)

    _deferred = True

    class Meta:
        proxy = True
