import contextlib
import datetime
import hashlib
import logging

from django.core import validators
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import DEFAULT_DB_ALIAS
from django.db import connection
from django.db import connections
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.deconstruct import deconstructible
import sentry_sdk

from share.models.core import ShareUser
from share.models.fields import EncryptedJSONField
from share.models.fuzzycount import FuzzyCountManager
from share.models.source_unique_identifier import SourceUniqueIdentifier
from share.util import chunked, placeholders, BaseJSONAPIMeta
from share.util.extensions import Extensions


logger = logging.getLogger(__name__)
__all__ = ('Source', 'SourceConfig', 'RawDatum', )


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


class NaturalKeyManager(models.Manager):
    use_in_migrations = True

    def __init__(self, *key_fields):
        super(NaturalKeyManager, self).__init__()
        self.key_fields = key_fields

    def get_by_natural_key(self, key):
        return self.get(**dict(zip(self.key_fields, key)))


class Source(models.Model):
    name = models.TextField(unique=True)
    long_title = models.TextField(unique=True)
    home_page = models.URLField(null=True, blank=True)
    icon = models.ImageField(upload_to=icon_name, storage=SourceIconStorage(), blank=True)
    is_deleted = models.BooleanField(default=False)

    # Whether or not this SourceConfig collects original content
    # If True changes made by this source cannot be overwritten
    # This should probably be on SourceConfig but placing it on Source
    # is much easier for the moment.
    # I also haven't seen a situation where a Source has two feeds that we harvest
    # where one provider unreliable metadata but the other does not.
    canonical = models.BooleanField(default=False, db_index=True)

    # TODO replace with object permissions, allow multiple sources per user (SHARE-996)
    user = models.OneToOneField('ShareUser', null=True, on_delete=models.CASCADE)

    objects = NaturalKeyManager('name')

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def natural_key(self):
        return (self.name,)

    def __repr__(self):
        return '<{}({}, {}, {})>'.format(self.__class__.__name__, self.pk, self.name, self.long_title)

    def __str__(self):
        return repr(self)


class SourceConfigManager(NaturalKeyManager):
    def get_or_create_push_config(self, user, transformer_key=None):
        assert isinstance(user, ShareUser)
        _config_label = '.'.join((
            user.username,
            transformer_key or 'rdf',  # TODO: something cleaner?
        ))
        try:
            _config = SourceConfig.objects.get(label=_config_label)
        except SourceConfig.DoesNotExist:
            _source, _ = Source.objects.get_or_create(
                user_id=user.id,
                defaults={
                    'name': user.username,
                    'long_title': user.username,
                }
            )
            _config, _ = SourceConfig.objects.get_or_create(
                label=_config_label,
                defaults={
                    'source': _source,
                    'transformer_key': transformer_key,
                }
            )
        assert _config.source.user_id == user.id
        assert _config.transformer_key == transformer_key
        return _config


class SourceConfig(models.Model):
    # Previously known as the provider's app_label
    label = models.TextField(unique=True)
    version = models.PositiveIntegerField(default=1)

    source = models.ForeignKey('Source', on_delete=models.CASCADE, related_name='source_configs')
    base_url = models.URLField(null=True)
    earliest_date = models.DateField(null=True, blank=True)
    rate_limit_allowance = models.PositiveIntegerField(default=5)
    rate_limit_period = models.PositiveIntegerField(default=1)

    # Allow null for push sources
    harvester_key = models.TextField(null=True)
    harvester_kwargs = models.JSONField(null=True, blank=True)
    harvest_interval = models.DurationField(default=datetime.timedelta(days=1))
    harvest_after = models.TimeField(default='02:00')
    full_harvest = models.BooleanField(default=False, help_text=(
        'Whether or not this SourceConfig should be fully harvested. '
        'Requires earliest_date to be set. '
        'The schedule harvests task will create all jobs necessary if this flag is set. '
        'This should never be set to True by default. '
    ))

    transformer_key = models.TextField(null=True)
    transformer_kwargs = models.JSONField(null=True, blank=True)

    regulator_steps = models.JSONField(null=True, blank=True)

    disabled = models.BooleanField(default=False)

    private_harvester_kwargs = EncryptedJSONField(blank=True, null=True)
    private_transformer_kwargs = EncryptedJSONField(blank=True, null=True)

    objects = SourceConfigManager('label')

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def natural_key(self):
        return (self.label,)

    def get_harvester_class(self):
        return Extensions.get('share.harvesters', self.harvester_key)

    def get_transformer_class(self):
        return Extensions.get('share.transformers', self.transformer_key)

    def get_harvester(self, **kwargs):
        """Return a harvester instance configured for this SourceConfig.

        **kwargs: passed to the harvester's initializer
        """
        return self.get_harvester_class()(self, **kwargs)

    def get_transformer(self, **kwargs):
        """Return a transformer instance configured for this SourceConfig.

        **kwargs: passed to the transformer's initializer
        """
        return self.get_transformer_class()(self, **kwargs)

    @contextlib.contextmanager
    def acquire_lock(self, required=True, using='default'):
        from share.harvest.exceptions import HarvesterConcurrencyError

        # NOTE: Must be in transaction
        logger.debug('Attempting to lock %r', self)
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s::regclass::integer, %s);", (self._meta.db_table, self.id))
            locked = cursor.fetchone()[0]
            if not locked and required:
                logger.warning('Lock failed; another task is already harvesting %r.', self)
                raise HarvesterConcurrencyError('Unable to lock {!r}'.format(self))
            elif locked:
                logger.debug('Lock acquired on %r', self)
            else:
                logger.warning('Lock not acquired on %r', self)
            try:
                yield
            finally:
                if locked:
                    cursor.execute("SELECT pg_advisory_unlock(%s::regclass::integer, %s);", (self._meta.db_table, self.id))
                    logger.debug('Lock released on %r', self)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.label)

    __str__ = __repr__


class RawDatumManager(FuzzyCountManager):

    def link_to_job(self, job, datum_ids):
        if not datum_ids:
            return True
        logger.debug('Linking RawData to %r', job)
        with connection.cursor() as cursor:
            for chunk in chunked(datum_ids, size=500):
                if not chunk:
                    break
                cursor.execute('''
                    INSERT INTO "{table}"
                        ("{rawdatum}", "{harvestjob}")
                    VALUES
                        {values}
                    ON CONFLICT ("{rawdatum}", "{harvestjob}") DO NOTHING;
                '''.format(
                    values=', '.join('%s' for _ in range(len(chunk))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    table=RawDatum.jobs.through._meta.db_table,
                    rawdatum=RawDatum.jobs.through._meta.get_field('rawdatum').column,
                    harvestjob=RawDatum.jobs.through._meta.get_field('harvestjob').column,
                ), [(raw_id, job.id) for raw_id in chunk])
        return True

    # TODO: remove `store_chunk` (and the rest of the non-rdf legacy pipeline)
    def store_chunk(self, source_config, data, limit=None, db=DEFAULT_DB_ALIAS):
        """Store a large amount of data for a single source_config.

        Data MUST be a utf-8 encoded string (Just a str type).
        Take special care to make sure you aren't destroying data by mis-encoding it.

        Args:
            source_config (SourceConfig):
            data Generator[FetchResult]:

        Returns:
            Generator[RawDatum]
        """
        hashes = {}
        identifiers = {}
        now = timezone.now()

        if limit == 0:
            return []

        for chunk in chunked(data, 500):
            if not chunk:
                break

            new = []
            new_identifiers = set()
            for fr in chunk:
                if limit and len(hashes) >= limit:
                    break

                if fr.sha256 in hashes:
                    if hashes[fr.sha256] != fr.identifier:
                        raise ValueError(
                            '{!r} has already been seen or stored with identifier "{}". '
                            'Perhaps your identifier extraction is incorrect?'.format(fr, hashes[fr.sha256])
                        )
                    logger.warning('Recieved duplicate datum %s from %s', fr, source_config)
                    continue

                new.append(fr)
                hashes[fr.sha256] = fr.identifier
                new_identifiers.add(fr.identifier)

            if new_identifiers:
                suids = SourceUniqueIdentifier.objects.raw('''
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
                    values=placeholders(len(new_identifiers)),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    fields=', '.join('"{}"'.format(field.column) for field in SourceUniqueIdentifier._meta.concrete_fields),
                ), [(identifier, source_config.id) for identifier in new_identifiers])

                for suid in suids:
                    identifiers[suid.identifier] = suid.pk

            if new:
                # Defer 'datum' by omitting it from the returned fields
                yield from RawDatum.objects.raw(
                    '''
                        INSERT INTO "{table}"
                            ("{suid}", "{hash}", "{datum}", "{datestamp}", "{date_modified}", "{date_created}")
                        VALUES
                            {values}
                        ON CONFLICT
                            ("{suid}", "{hash}")
                        DO UPDATE SET
                            "{datestamp}" = EXCLUDED."{datestamp}",
                            "{date_modified}" = EXCLUDED."{date_modified}"
                        RETURNING id, "{suid}", "{hash}", "{datestamp}", "{date_modified}", "{date_created}"
                    '''.format(
                        table=RawDatum._meta.db_table,
                        suid=RawDatum._meta.get_field('suid').column,
                        hash=RawDatum._meta.get_field('sha256').column,
                        datum=RawDatum._meta.get_field('datum').column,
                        datestamp=RawDatum._meta.get_field('datestamp').column,
                        date_modified=RawDatum._meta.get_field('date_modified').column,
                        date_created=RawDatum._meta.get_field('date_created').column,
                        values=', '.join('%s' for _ in range(len(new))),  # Nasty hack. Fix when psycopg2 2.7 is released with execute_values
                    ), [
                        (identifiers[fr.identifier], fr.sha256, fr.datum, fr.datestamp or now, now, now)
                        for fr in new
                    ]
                )

            if limit and len(hashes) >= limit:
                break

    def store_data(self, config, fetch_result):
        """
        """
        (rd, ) = self.store_chunk(config, [fetch_result])

        if rd.created:
            logger.debug('New %r', rd)
        else:
            logger.debug('Found existing %r', rd)

        return rd

    def store_datum_for_suid(
        self,
        *,
        suid,
        datum: str,
        mediatype: str | None,  # `None` indicates sharev2-legacy ingestion
        datestamp: datetime.datetime,
        expiration_date: datetime.date | None = None,
    ):
        _raw, _raw_created = self.get_or_create(
            suid=suid,
            sha256=hashlib.sha256(datum.encode()).hexdigest(),
            defaults={
                'datum': datum,
                'mediatype': mediatype,
                'datestamp': datestamp,
                'expiration_date': expiration_date,
            },
        )
        if not _raw_created:
            if _raw.datum != datum:
                _msg = f'hash collision!? {_raw.sha256}\n===\n{_raw.datum}\n===\n{datum}'
                logger.critical(_msg)
                sentry_sdk.capture_message(_msg)
            _raw.mediatype = mediatype
            _raw.expiration_date = expiration_date
            # keep the latest datestamp
            if (not _raw.datestamp) or (datestamp > _raw.datestamp):
                _raw.datestamp = datestamp
            _raw.save(update_fields=('mediatype', 'datestamp', 'expiration_date'))
        return _raw

    def latest_by_suid_id(self, suid_id) -> models.QuerySet:
        return self.latest_by_suid_queryset(
            SourceUniqueIdentifier.objects.filter(id=suid_id),
        )

    def latest_by_suid_queryset(self, suid_queryset) -> models.QuerySet:
        return self.filter(id__in=(
            suid_queryset
            .annotate(latest_rawdatum_id=models.Subquery(
                RawDatum.objects
                .filter(suid_id=models.OuterRef('id'))
                .order_by(Coalesce('datestamp', 'date_created').desc(nulls_last=True))
                .values('id')
                [:1]
            ))
            .values('latest_rawdatum_id')
        ))


# Explicit through table to match legacy names
class RawDatumJob(models.Model):
    datum = models.ForeignKey('RawDatum', db_column='rawdatum_id', on_delete=models.CASCADE)
    job = models.ForeignKey('HarvestJob', db_column='harvestlog_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'share_rawdatum_logs'


class RawDatum(models.Model):

    datum = models.TextField()
    mediatype = models.TextField(null=True, blank=True)

    suid = models.ForeignKey(SourceUniqueIdentifier, on_delete=models.CASCADE, related_name='raw_data')

    # The sha256 of the datum
    sha256 = models.TextField(validators=[validators.MaxLengthValidator(64)])

    datestamp = models.DateTimeField(null=True, help_text=(
        'The most relevant datetime that can be extracted from this RawDatum. '
        'This may be, but is not limited to, a deletion, modification, publication, or creation datestamp. '
        'Ideally, this datetime should be appropriate for determining the chronological order its data will be applied.'
    ))
    expiration_date = models.DateField(
        null=True,
        blank=True,
        help_text='An (optional) date after which this datum is no longer valid.',
    )

    date_modified = models.DateTimeField(auto_now=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    no_output = models.BooleanField(null=True, help_text=(
        'Indicates that this RawDatum resulted in an empty graph when transformed. '
        'This allows the RawDataJanitor to find records that have not been processed. '
        'Records that result in an empty graph will not have a NormalizedData associated with them, '
        'which would otherwise look like data that has not yet been processed.'
    ))

    jobs = models.ManyToManyField('HarvestJob', related_name='raw_data', through=RawDatumJob)

    objects = RawDatumManager()

    @property
    def created(self):
        return self.date_modified == self.date_created

    def is_latest(self):
        return (
            RawDatum.objects
            .latest_by_suid_id(self.suid_id)
            .filter(id=self.id)
            .exists()
        )

    @property
    def is_expired(self) -> bool:
        return (
            self.expiration_date is not None
            and self.expiration_date <= datetime.date.today()
        )

    class Meta:
        unique_together = ('suid', 'sha256')
        verbose_name_plural = 'Raw Data'
        indexes = [
            models.Index(fields=['no_output'], name='share_rawda_no_outp_f0330f_idx'),
            models.Index(fields=['expiration_date'], name='share_rawdatum_expiration_idx'),
        ]

    class JSONAPIMeta(BaseJSONAPIMeta):
        resource_name = 'RawData'

    def __repr__(self):
        return '<{}({}, {}, {}...)>'.format(self.__class__.__name__, self.id, self.datestamp, self.sha256[:10])

    __str__ = __repr__
