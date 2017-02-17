from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.files.storage import Storage
from django.db import models
from django.utils.deconstruct import deconstructible

from db.deletion import DATABASE_CASCADE

from share.models.fuzzycount import FuzzyCountManager

import datetime
import logging
import traceback
from hashlib import sha256

from model_utils import Choices

from django.conf import settings
from django.db import connection
# from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
# from django.contrib.auth.models import PermissionsMixin, Group
from django.core import validators
# from django.core.files.base import ContentFile
# from django.core.files.storage import Storage
from django.db import models
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.core.urlresolvers import reverse
# from django.utils import timezone
# from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
# from oauth2_provider.models import AccessToken, Application

# from db.deletion import DATABASE_CASCADE

# from osf_oauth2_adapter.apps import OsfOauth2AdapterConfig

# from share.models.fields import DateTimeAwareJSONField, ShareURLField
from share.models.fuzzycount import FuzzyCountManager
from share.util import chunked
# from share.models.validators import JSONLDValidator


logger = logging.getLogger(__name__)
__all__ = ('Source', 'HarvestLog', 'RawDatum', 'SourceConfig', 'Harvester', 'Transformer')


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


class SourceConfig(models.Model):
    # Previously known as the provider's app_label
    label = models.TextField(unique=True)

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


class Harvester(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    def natural_key(self):
        return self.key

    def get_class(self):
        from share.harvest import BaseHarvester
        return BaseHarvester.registry[self.key]

    @property
    def version(self):
        return self.get_class().VERSION


class Transformer(models.Model):
    key = models.TextField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = NaturalKeyManager('key')

    def natural_key(self):
        return self.key

    def get_class(self):
        from share.transform import BaseTransformer
        return BaseTransformer.registry[self.key]

    @property
    def version(self):
        return self.get_class().VERSION


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
            exception = tb.format(chain=True)

        self.status = HarvestLog.STATUS.rescheduled
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
        logger.debug('Linking RawData to %r', log)
        with connection.cursor() as cursor:
            for chunk in chunked(datum_ids, size=500):
                cursor.excecute('''
                    INSERT INTO "{table}"
                        ("{rawdata}", "{harvesterlog}")
                    VALUES
                        %s
                    ON CONFLICT ("{rawdata}", "{harvesterlog}") DO NOTHING;
                '''.format(
                    table=RawDatum.logs.through._meta.table_name,
                    rawdata=RawDatum.logs.through._meta.get_field('rawdata').column_name,
                    harvestlog=RawDatum.logs.through._meta.get_field('harvestlog').column_name,
                ), tuple((raw_id, log.id) for raw_id in chunk))
        return True

    def store_data(self, identifier, data, config):
        suid, _ = SourceUniqueIdentifier.objects.get_or_create(identifier=identifier, config=config)
        rd, created = self.get_or_create(suid=suid, data=data, sha256=sha256(data).hexdigest())

        if created:
            logger.debug('New RawDatum for %r', suid)
        else:
            logger.debug('Found existing RawDatum for %r', suid)

        return rd


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

    logs = models.ManyToManyField('HarvestLog')

    objects = RawDatumManager()

    class Meta:
        unique_together = ('suid', 'sha256')
        verbose_name_plural = 'Raw Data'

    def __repr__(self):
        return '<{}({!r}, {})>'.format(self.__class__.__name__, self.suid, self.sha256)

    __str__ = __repr__
