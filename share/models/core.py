import datetime
import logging
import random
import string

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, Group
from django.core import validators
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oauth2_provider.models import AccessToken, Application

from osf_oauth2_adapter.apps import OsfOauth2AdapterConfig

from share.models.fields import DateTimeAwareJSONField, ShareURLField
from share.models.validators import JSONLDValidator

logger = logging.getLogger(__name__)
__all__ = ('ShareUser', 'NormalizedData',)


class ShareUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, save=True, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        ShareUser.set_password(user, password)
        if save:
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
            self.get(username=username, robot=robot)
        except self.model.DoesNotExist:
            pass
        else:
            raise AssertionError('ShareUser for robot {} already exists.'.format(robot))
        user = self.model()
        ShareUser.set_unusable_password(user)
        user.username = username
        user.robot = robot
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save()
        return user


class ShareUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    username = models.TextField(
        _('username'),
        unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[
            validators.MaxLengthValidator(64),
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
    first_name = models.TextField(_('first name'), validators=[validators.MaxLengthValidator(64)], blank=True)
    last_name = models.TextField(_('last name'), validators=[validators.MaxLengthValidator(64)], blank=True)
    email = models.EmailField(_('email address'), blank=True)
    gravatar = ShareURLField(blank=True)
    time_zone = models.TextField(validators=[validators.MaxLengthValidator(100)], blank=True)
    locale = models.TextField(validators=[validators.MaxLengthValidator(100)], blank=True)
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
    is_trusted = models.BooleanField(
        _('trusted'),
        default=False,
        help_text=_('Designates whether the user can push directly into the db.'),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    robot = models.TextField(validators=[validators.MaxLengthValidator(40)], blank=True)

    objects = ShareUserManager()

    USERNAME_FIELD = 'username'

    class Meta:
        verbose_name = _('Share user')
        verbose_name_plural = _('Share users')

    @property
    def is_robot(self):
        return self.robot != ''

    def get_short_name(self):
        return self.robot if self.is_robot else self.username

    def get_full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def authorization(self) -> str:
        return 'Bearer ' + self.accesstoken_set.first().token

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.username)

    def __str__(self):
        return repr(self)


@receiver(post_save, sender=ShareUser, dispatch_uid='share.share.models.share_user_post_save_handler')
def user_post_save(sender, instance, created, **kwargs):
    """
    If the user is being created and they're a robot:
        make them an oauth token with harvester scopes.
    If the user is being created and they're not a robot:
        make them an oauth token with user scopes.
        add them to the humans group.
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created and instance.username not in (settings.APPLICATION_USERNAME, settings.ANONYMOUS_USER_NAME):
        application_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        application = Application.objects.get(user=application_user)
        client_secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))

        is_robot = instance.robot != ''  # Required to work in migrations and the like

        # create oauth2 token for user
        AccessToken.objects.create(
            user_id=instance.id,
            application=application,
            expires=(timezone.now() + datetime.timedelta(weeks=20 * 52)),  # 20 yrs
            scope=settings.HARVESTER_SCOPES if is_robot else settings.USER_SCOPES,
            token=client_secret
        )
        if not is_robot:
            instance.groups.add(Group.objects.get(name=OsfOauth2AdapterConfig.humans_group_name))


class NormalizedData(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    raw = models.ForeignKey('RawDatum', null=True, on_delete=models.CASCADE)
    data = DateTimeAwareJSONField(validators=[JSONLDValidator(), ])
    source = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tasks = models.ManyToManyField('CeleryTaskResult')

    def __str__(self):
        return '{} created at {}'.format(self.source.get_short_name(), self.created_at)
