"""
Django settings for share project.

Generated by 'django-admin startproject' using Django 1.9.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import subprocess

from django.utils.log import DEFAULT_LOGGING

from kombu import Queue, Exchange

# Suppress select django deprecation messages
LOGGING = DEFAULT_LOGGING
LOGGING_CONFIG = 'project.log.configure'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'c^0=k9r3i2@kh=*=(w2r_-sc#fd!+b23y%)gs+^0l%=bt_dst0')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DEBUG', True))

if 'VERSION' not in os.environ and DEBUG:
    try:
        VERSION = subprocess.check_output(['git', 'describe']).decode().strip()
    except subprocess.CalledProcessError:
        VERSION = 'UNKNOWN'
else:
    VERSION = os.environ.get('VERSION') or 'UNKNOWN'

ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '').split(' ') if h]

AUTH_USER_MODEL = 'share.ShareUser'

JSON_API_FORMAT_KEYS = 'camelize'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'djcelery',
    # 'guardian',
    'django_filters',
    'django_extensions',
    'oauth2_provider',
    'rest_framework',
    'corsheaders',
    'revproxy',
    'graphene_django',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # not yet
    # 'allauth.socialaccount.providers.orcid',
    # 'allauth.socialaccount.providers.github',
    # 'allauth.socialaccount.providers.google',
    'osf_oauth2_adapter',

    'share',
    'api',

    'bots.archive',
    'bots.elasticsearch',
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
SOCIALACCOUNT_ADAPTER = 'osf_oauth2_adapter.views.OSFOAuth2Adapter'
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
        'api.renderers.HideNullJSONAPIRenderer',
        # 'rest_framework_json_api.renderers.JSONRenderer',
        # 'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticatedOrReadOnly',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
        # 'api.authentication.NonCSRFSessionAuthentication',
    ),
}

GRAPHENE = {
    'SCHEMA': 'share.graphql.schema'
}

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
        'ENGINE': 'db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'share'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', None),
        'CONN_MAX_AGE': os.environ.get('CONN_MAX_AGE', None),
        'TEST': {'SERIALIZE': False},
    },
    'locking': {
        'ENGINE': 'db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'share'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', None),
        'CONN_MAX_AGE': os.environ.get('CONN_MAX_AGE', None),
        'TEST': {'MIRROR': 'default', 'SERIALIZE': False},
    }
}

# DATABASES['locking'] = DATABASES['default']

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
# else:
if os.environ.get('USE_SENTRY'):
    INSTALLED_APPS += [
        'raven.contrib.django.raven_compat',
    ]
    RAVEN_CONFIG = {
        'dsn': os.environ.get('SENTRY_DSN', None),
        'release': os.environ.get('GIT_COMMIT', None),
    }


# TODO REMOVE BEFORE PRODUCTION
# ALLOW LOCAL USERS TO SEARCH
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
# TODO REMOVE BEFORE PRODUCTION

ANONYMOUS_USER_NAME = 'AnonymousUser'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
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
    os.path.join(
        os.path.dirname(__file__),
        'static'
    ),
)

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200/')
ELASTICSEARCH_INDEX = os.environ.get('ELASTIC_SEARCH_INDEX', 'share')
ELASTICSEARCH_TIMEOUT = int(os.environ.get('ELASTICSEARCH_TIMEOUT', '45'))
ELASTICSEARCH_INDEX_VERSIONS = tuple(v for v in os.environ.get('ELASTICSEARCH_INDEX_VERSIONS', '').split(',') if v)

# Seconds, not an actual celery settings
CELERY_RETRY_BACKOFF_BASE = int(os.environ.get('CELERY_RETRY_BACKOFF_BASE', 2 if DEBUG else 10))

# Celery Settings

BROKER_URL = os.environ.get('BROKER_URL', 'amqp://'),

CELERY_TIMEZONE = 'UTC'
CELERYBEAT_SCHEDULE = {}

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_ACKS_LATE = True
# CELERY_TRACK_STARTED = True
CELERY_RESULT_PERSISTENT = True
# CELERY_SEND_EVENTS = True
# CELERY_SEND_TASK_SENT_EVENT = True
CELERY_LOADER = 'djcelery.loaders.DjangoLoader'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_RESULT_BACKEND = 'share.celery:DatabaseBackend'

# Celery Queues
QUEUES = {
    'DEFAULT': {
        'name': 'celery',
        'priority': 0,
        'modules': set(),
    },
    'GEVENT': {
        'name': 'gevent',
        'priority': 0,
        'modules': {'bots.elasticsearch', },
    },
    'LOW': {
        'name': 'low',
        'priority': -10,
        'modules': {'share.tasks.HarvesterTask', },
    },
    'MED': {
        'name': 'med',
        'priority': 20,
        'modules': {'share.tasks.DisambiguatorTask', },
    },
    'HIGH': {
        'name': 'high',
        'priority': 30,
        'modules': {'share.tasks.BotTask', },
    },
    'BACKHARVEST': {
        'name': 'backharvest',
        'priority': -20,
        'modules': set(),
    }
}

CELERY_QUEUES = tuple(
    Queue(
        v['name'],
        Exchange(v['name']),
        routing_key=v['name'],
        consumer_arguments={'x-priority': v['priority']}
    ) for v in QUEUES.values()
)

CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_ROUTES = ('share.celery.CeleryRouter', )
CELERY_IGNORE_RESULT = True
CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(levelname)s][%(name)s]: %(reset)s%(message)s'
        }
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',  # To capture more than ERROR, change to WARNING, INFO, etc.
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'tags': {'custom-tag': 'x'},
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'console'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'bots': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False
        },
        'providers': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False
        },
        'share': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    }
}

# shell_plus convenience utilities
SHELL_PLUS_POST_IMPORTS = (
    ('share.shell_util', '*'),
)


# Custom Settings
SITE_ID = 1
PUBLIC_SENTRY_DSN = os.environ.get('PUBLIC_SENTRY_DSN')

EMBER_SHARE_PREFIX = os.environ.get('EMBER_SHARE_PREFIX', 'share' if DEBUG else '')
EMBER_SHARE_URL = os.environ.get('EMBER_SHARE_URL', 'http://localhost:4200').rstrip('/') + '/'
SHARE_API_URL = os.environ.get('SHARE_API_URL', 'http://localhost:8000').rstrip('/') + '/'
SHARE_WEB_URL = os.environ.get('SHARE_WEB_URL', SHARE_API_URL + EMBER_SHARE_PREFIX).rstrip('/') + '/'

OSF_API_URL = os.environ.get('OSF_API_URL', 'https://staging-api.osf.io').rstrip('/') + '/'
DOI_BASE_URL = os.environ.get('DOI_BASE_URL', 'http://dx.doi.org/')

ALLOWED_TAGS = ['abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul']

# API KEYS
DATAVERSE_API_KEY = os.environ.get('DATAVERSE_API_KEY')
PLOS_API_KEY = os.environ.get('PLOS_API_KEY')
SPRINGER_API_KEY = os.environ.get('SPRINGER_API_KEY')
RESEARCHREGISTRY_APPLICATION_ID = os.environ.get('RESEARCHREGISTRY_APPLICATION_ID', '54a1ac1032e4beb07e04ac2c')
RESEARCHREGISTRY_API_KEY = os.environ.get('RESEARCHREGISTRY_API_KEY', 'renderer')

# Amazon Web Services Credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
CELERY_TASK_BUCKET_NAME = os.environ.get('CELERY_TASK_BUCKET_NAME')
CELERY_TASK_FOLDER_NAME = os.environ.get('CELERY_TASK_FOLDER_NAME')  # top level folder (e.g. prod, staging)


import djcelery  # noqa
djcelery.setup_loader()

if DEBUG and os.environ.get('TOOLBAR', False):
    INSTALLED_APPS += ('debug_toolbar', )
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda _: True
    }
    ALLOWED_HOSTS.append('localhost')
