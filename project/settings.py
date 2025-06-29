"""
Django settings for share project.

Generated by 'django-admin startproject' using Django 1.9.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

from celery.schedules import crontab
import jwe

from share import __version__
from trove.util.queryparams import parse_booly_str


def split(string, delim):
    return tuple(map(str.strip, filter(None, string.split(delim))))


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'c^0=k9r3i2@kh=*=(w2r_-sc#fd!+b23y%)gs+^0l%=bt_dst0')

SALT = os.environ.get('SALT', 'r_-78y%c^(w2_ds0d*=t!+c=s+^0l=bt%2isc#f2@kh=0k5r)g')

SENSITIVE_DATA_KEY = jwe.kdf(SECRET_KEY.encode('utf-8'), SALT.encode('utf-8'))


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DEBUG', True))

VERSION = __version__
GIT_COMMIT = os.environ.get('GIT_COMMIT', None)

ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '').split(' ') if h]

AUTH_USER_MODEL = 'share.ShareUser'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

JSON_API_FORMAT_FIELD_NAMES = 'camelize'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'django_celery_beat',

    'django_filters',
    'django_extensions',
    'oauth2_provider',
    'rest_framework',
    'corsheaders',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # not yet
    # 'allauth.socialaccount.providers.orcid',
    # 'allauth.socialaccount.providers.github',
    # 'allauth.socialaccount.providers.google',
    'osf_oauth2_adapter',

    'share',
    'trove',
    'api',
]

HARVESTER_SCOPES = 'upload_normalized_manuscript upload_raw_data'
USER_SCOPES = 'approve_changesets'

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'groups': 'Access to your groups',
        'upload_normalized_manuscript': 'Upload Normalized Manuscript',
        'upload_raw_data': 'Upload Raw Data',
        'approve_changesets': 'Approve ChangeSets'
    }
}
SOCIALACCOUNT_ADAPTER = 'osf_oauth2_adapter.adapters.OSFSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = \
    {'osf':
        {
            'METHOD': 'oauth2',
            'SCOPE': ['osf.users.profile_read'],
            'AUTH_PARAMS': {'access_type': 'offline'},
            # 'FIELDS': [
            #     'id',
            #     'email',
            #     'name',
            #     'first_name',
            #     'last_name',
            #     'verified',
            #     'locale',
            #     'timezone',
            #     'link',
            #     'gender',
            #     'updated_time'],
            # 'EXCHANGE_TOKEN': True,
            # 'LOCALE_FUNC': 'path.to.callable',
            # 'VERIFIED_EMAIL': False,
            # 'VERSION': 'v2.4'
        }
     }


APPLICATION_USERNAME = 'system'

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'ORDERING_PARAM': 'sort',
    'EXCEPTION_HANDLER': 'rest_framework_json_api.exceptions.exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.FuzzyPageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_json_api.parsers.JSONParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
        # 'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticatedOrReadOnly',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
        # 'api.authentication.NonCSRFSessionAuthentication',
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.DeprecationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'share'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', None),
        'CONN_MAX_AGE': int(os.environ.get('CONN_MAX_AGE', 0)),
    },
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_REDIRECT_URL = os.environ.get('LOGIN_REDIRECT_URL', 'http://localhost:8000/')

if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []

if os.environ.get('USE_SENTRY'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN', None),
        release=(
            '-'.join((VERSION, GIT_COMMIT))
            if GIT_COMMIT
            else VERSION
        ),
        send_default_pii=False,
        request_bodies='never',
        debug=DEBUG,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
        ],
    )


if True:  # TODO: if DEBUG:
    # ALLOW LOCAL USERS TO SEARCH
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True

ANONYMOUS_USER_NAME = 'AnonymousUser'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'oauth2_provider.backends.OAuth2Backend',
    'allauth.account.auth_backends.AuthenticationBackend',
    # 'guardian.backends.ObjectPermissionBackend',
)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'static'),
)

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

ELASTICSEARCH = {
    'SNIFF': bool(os.environ.get('ELASTICSEARCH_SNIFF')),
    'TIMEOUT': int(os.environ.get('ELASTICSEARCH_TIMEOUT', '45')),
    'CHUNK_SIZE': int(os.environ.get('ELASTICSEARCH_CHUNK_SIZE', 2000)),
    'MAX_RETRIES': int(os.environ.get('ELASTICSEARCH_MAX_RETRIES', 7)),
    'POST_INDEX_DELAY': int(os.environ.get('ELASTICSEARCH_POST_INDEX_DELAY', 3)),
}
ELASTICSEARCH5_URL = (
    os.environ.get('ELASTICSEARCH5_URL')
    or os.environ.get('ELASTICSEARCH_URL')  # backcompat
)
ELASTICSEARCH8_URL = os.environ.get('ELASTICSEARCH8_URL')
ELASTICSEARCH8_CERT_PATH = os.environ.get('ELASTICSEARCH8_CERT_PATH')
ELASTICSEARCH8_USERNAME = os.environ.get('ELASTICSEARCH8_USERNAME', 'elastic')
ELASTICSEARCH8_SECRET = os.environ.get('ELASTICSEARCH8_SECRET')

# Seconds, not an actual celery settings
CELERY_RETRY_BACKOFF_BASE = int(os.environ.get('CELERY_RETRY_BACKOFF_BASE', 2 if DEBUG else 10))

# Celery Settings

CELERY_TIMEZONE = 'UTC'

# Default RabbitMQ broker
RABBITMQ_USERNAME = os.environ.get('RABBITMQ_USERNAME', 'guest')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', '5672')
RABBITMQ_MGMT_PORT = os.environ.get('RABBITMQ_MGMT_PORT', '15672')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', '/')
RABBITMQ_HEARTBEAT_TIMEOUT = int(os.environ.get('RABBITMQ_HEARTBEAT_TIMEOUT', 60))

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'amqp://{}:{}@{}:{}/{}'.format(RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST))

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'Expel expired data': {
        'task': 'trove.digestive_tract.task__expel_expired_data',
        'schedule': crontab(hour=0, minute=0),  # every day at midnight UTC
    },
}

CELERY_RESULT_BACKEND = 'share.celery:CeleryDatabaseBackend'
CELERY_RESULT_EXPIRES = int(os.environ.get(
    'CELERY_RESULT_EXPIRES',
    60 * 60 * 24 * 3,  # 3 days
))
# only successful tasks get the default expiration (above)
# -- failed tasks kept longer (see `share.celery`)
FAILED_CELERY_RESULT_EXPIRES = int(os.environ.get(
    'FAILED_CELERY_RESULT_EXPIRES',
    60 * 60 * 24 * 11,  # 11 days
))

# Don't reject tasks that were present on a worker when it was killed
CELERY_TASK_REJECT_ON_WORKER_LOST = False

# Don't remove tasks from RabbitMQ until they are finished
CELERY_TASK_ACKS_LATE = True

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60 * 3  # 3 Hours

CELERY_TASK_DEFAULT_QUEUE = 'share_default'
CELERY_TASK_DEFAULT_EXCHANGE = 'share_default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'share_default'

URGENT_TASK_QUEUES = {
    'trove.digestive_tract.task__derive': 'digestive_tract.urgent',
}


def route_urgent_task(name, args, kwargs, options, task=None, **kw):
    """Allow routing urgent tasks to a special queue, according to URGENT_TASK_QUEUES

    e.g. task.apply_async(args, {**kwargs, urgent=True})
    """
    # TODO: consider using routing_key instead?
    if name in URGENT_TASK_QUEUES and kwargs.get('urgent'):
        return {'queue': URGENT_TASK_QUEUES[name]}


CELERY_TASK_ROUTES = [
    route_urgent_task,
    {
        'trove.digestive_tract.*': {'queue': 'digestive_tract'},
    },
]
CELERY_TASK_QUEUES = {
    'share_default': {},
    'elasticsearch': {},
    'digestive_tract': {},
    'digestive_tract.urgent': {},
}


# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', default='INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(cyan)s[%(asctime)s]%(purple)s[%(threadName)s]%(log_color)s[%(levelname)s][%(name)s]: %(reset)s%(message)s'
        },
        'json': {
            '()': 'project.logging_formatter.JsonLogFormatter',
            'format': '[%(asctime)s][%(threadName)s][%(levelname)s][%(name)s]: %(message)s'
        },
    },
    'handlers': {
        'stream-to-stderr': {
            'class': 'logging.StreamHandler',
            'level': LOG_LEVEL,
            'formatter': ('console' if DEBUG else 'json'),
        },
    },
    'loggers': {
        '': {
            'level': LOG_LEVEL,
            'handlers': ['stream-to-stderr'],
            'propagate': False
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['stream-to-stderr'],
            'propagate': False,
        },
        'elastic_transport.transport': {
            'level': 'ERROR',
            'handlers': ['stream-to-stderr'],
            'propagate': False,
        },
    },
}

# shell_plus convenience utilities
SHELL_PLUS_POST_IMPORTS = (
    ('share.shell_util', '*'),
)


# Custom Settings
SITE_ID = 1
PUBLIC_SENTRY_DSN = os.environ.get('PUBLIC_SENTRY_DSN')

SHARE_WEB_URL = os.environ.get('SHARE_WEB_URL', 'http://localhost:8003').rstrip('/') + '/'
SHARE_USER_AGENT = os.environ.get('SHARE_USER_AGENT', 'SHAREbot/{} (+{})'.format(VERSION, SHARE_WEB_URL))
SHARE_ADMIN_USERNAME = os.environ.get('SHARE_ADMIN_USERNAME', 'admin')
SHARE_ADMIN_PASSWORD = os.environ.get('SHARE_ADMIN_PASSWORD')
if DEBUG and (SHARE_ADMIN_PASSWORD is None):
    SHARE_ADMIN_PASSWORD = 'password'

# Skip some of the more intensive operations on works that surpass these limits
SHARE_LIMITS = {
    'MAX_IDENTIFIERS': 50,
    'MAX_AGENT_RELATIONS': 500,
}

OSF_API_URL = os.environ.get('OSF_API_URL', 'http://localhost:8000').rstrip('/') + '/'
OSF_BYPASS_THROTTLE_TOKEN = os.environ.get('BYPASS_THROTTLE_TOKEN', None)

DOI_BASE_URL = os.environ.get('DOI_BASE_URL', 'http://dx.doi.org/')

ALLOWED_TAGS = ['abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul']

SUBJECTS_CENTRAL_TAXONOMY = os.environ.get('SUBJECTS_CENTRAL_TAXONOMY', 'bepress')

HIDE_DEPRECATED_VIEWS = parse_booly_str(os.environ.get('HIDE_DEPRECATED_VIEWS', 'False'))

# Regulator pipeline, names of setuptools entry points
SHARE_REGULATOR_CONFIG = {
    'NODE_STEPS': [
        'tokenize_tags',
        'whitespace',
        'normalize_agent_names',
        'cited_as',
        ('normalize_iris', {
            'node_types': ['workidentifier'],
            'blocked_schemes': ['mailto'],
            'blocked_authorities': ['issn', 'orcid.org'],
        }),
        ('normalize_iris', {
            'node_types': ['agentidentifier'],
            'blocked_schemes': ['mailto'],
            'blocked_authorities': ['secure.gravatar.com'],
        }),
        ('trim_cycles', {
            'node_types': ['abstractworkrelation', 'abstractagentrelation'],
            'relation_fields': ['subject', 'related'],
        }),
        ('trim_cycles', {
            'node_types': ['subject'],
            'relation_fields': ['central_synonym'],
            'delete_node': False,
        }),
    ],
    'GRAPH_STEPS': [
        'deduplicate',
    ],
    'VALIDATE_STEPS': [
        'jsonld_validator',
    ],
}

# API KEYS
DATAVERSE_API_KEY = os.environ.get('DATAVERSE_API_KEY')
PLOS_API_KEY = os.environ.get('PLOS_API_KEY')
SPRINGER_API_KEY = os.environ.get('SPRINGER_API_KEY')
RESEARCHREGISTRY_APPLICATION_ID = os.environ.get('RESEARCHREGISTRY_APPLICATION_ID', '54a1ac1032e4beb07e04ac2c')
RESEARCHREGISTRY_API_KEY = os.environ.get('RESEARCHREGISTRY_API_KEY', 'renderer')
MENDELEY_API_CLIENT_ID = os.environ.get('MENDELEY_API_CLIENT_ID')
MENDELEY_API_CLIENT_SECRET = os.environ.get('MENDELEY_API_CLIENT_SECRET')

# Amazon Web Services Credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
CELERY_TASK_BUCKET_NAME = os.environ.get('CELERY_TASK_BUCKET_NAME')
CELERY_TASK_FOLDER_NAME = os.environ.get('CELERY_TASK_FOLDER_NAME')  # top level folder (e.g. prod, staging)


if DEBUG and os.environ.get('TOOLBAR', False):
    INSTALLED_APPS += ('debug_toolbar', )
    MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware', )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda _: True
    }
    ALLOWED_HOSTS.append('localhost')
