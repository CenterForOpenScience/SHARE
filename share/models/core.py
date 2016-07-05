import logging
from hashlib import sha256

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, Group
from django.core import validators
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from fuzzycount import FuzzyCountManager

from osf_oauth2_adapter.apps import OsfOauth2AdapterConfig
from share.models.fields import ZipField, DatetimeAwareJSONField
from share.models.validators import is_valid_jsonld

logger = logging.getLogger(__name__)
__all__ = ('ShareUser', 'RawData', 'NormalizedData',)


class ShareUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, password, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

    def create_robot_user(self, username, robot):
        try:
            ShareUser.objects.get(robot=robot)
        except ShareUser.DoesNotExist:
            pass
        else:
            raise AssertionError('ShareUser for robot {} already exists.'.format(robot))
        user = ShareUser()
        user.set_unusable_password()
        user.username = username
        user.robot = robot
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save()
        return user


class ShareUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    username = models.CharField(
        _('username'),
        max_length=64,
        unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[
            validators.RegexValidator(
                r'^[\w.@+-]+$',
                _('Enter a valid username. This value may contain only '
                  'letters, numbers ' 'and @/./+/-/_ characters.')
            ),
        ],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=64, blank=True)
    last_name = models.CharField(_('last name'), max_length=64, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    robot = models.CharField(max_length=40, blank=True)

    def get_short_name(self):
        return self.robot if self.is_robot else self.username

    def get_full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @property
    def is_robot(self):
        return self.robot != ''

    objects = ShareUserManager()

    USERNAME_FIELD = 'username'

    class Meta:
        verbose_name = _('Share user')
        verbose_name_plural = _('Share users')


@receiver(post_save, sender=ShareUser, dispatch_uid='share.share.models.share_user_post_save_handler')
def user_post_save(sender, instance, created, **kwargs):
    """
    If the user is being created and they're not a robot add them to the humans group.
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created and not instance.is_robot:

        instance.groups.add(Group.objects.get(name=OsfOauth2AdapterConfig.humans_group_name))


class RawDataManager(FuzzyCountManager):

    def store_data(self, doc_id, data, source):
        rd, created = self.get_or_create(
            source=source,
            provider_doc_id=doc_id,
            sha256=sha256(data).hexdigest(),
            defaults={'data': data},
        )

        if created:
            logger.debug('Newly created RawData for document {} from {}'.format(doc_id, source))
        else:
            logger.debug('Saw exact copy of document {} from {}'.format(doc_id, source))

        rd.save()  # Force timestamps to update
        return rd


class RawData(models.Model):
    id = models.AutoField(primary_key=True)

    source = models.ForeignKey(settings.AUTH_USER_MODEL)
    provider_doc_id = models.CharField(max_length=256)

    data = ZipField(blank=False)
    sha256 = models.CharField(max_length=64)

    date_seen = models.DateTimeField(auto_now=True)
    date_harvested = models.DateTimeField(auto_now_add=True)

    tasks = models.ManyToManyField('CeleryProviderTask')

    objects = RawDataManager()

    def __str__(self):
        return '({}) {} {}'.format(self.id, self.source, self.provider_doc_id)

    @property
    def processsed(self):
        return self.date_processed is not None  # TODO: this field doesn't exist...

    class Meta:
        unique_together = (('provider_doc_id', 'source', 'sha256'),)
        verbose_name_plural = 'Raw data'

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.source, self.provider_doc_id)


class NormalizedData(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(null=True)
    raw = models.ForeignKey(RawData, null=True)
    normalized_data = DatetimeAwareJSONField(default={}, validators=[is_valid_jsonld, ])
    source = models.ForeignKey(settings.AUTH_USER_MODEL)
    tasks = models.ManyToManyField('CeleryProviderTask')

    def __str__(self):
        return '{} created at {}'.format(self.source.get_short_name(), self.created_at)
