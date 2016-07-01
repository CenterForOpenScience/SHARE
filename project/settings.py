"""
Django settings for share project.

Generated by 'django-admin startproject' using Django 1.9.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
from django.utils.log import DEFAULT_LOGGING

# Suppress select django deprecation messages
LOGGING = DEFAULT_LOGGING
LOGGING_CONFIG = 'project.log.configure'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'c^0=k9r3i2@kh=*=(w2r_-sc#fd!+b23y%)gs+^0l%=bt_dst0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DEBUG', True))

ALLOWED_HOSTS = []

AUTH_USER_MODEL = 'share.ShareUser'

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
    'guardian',
    'django_filters',
    'django_extensions',
    'oauth2_provider',
    'rest_framework',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    'osf_oauth2_adapter',

    'share',
    'api',

    'bots.automerge',
    'bots.elasticsearch',

    'providers.be.ghent',
    'providers.br.pcurio',
    'providers.ca.lwbin',
    'providers.com.biomedcentral',
    'providers.com.dailyssrn',
    'providers.com.figshare',
    'providers.com.nature',
    'providers.edu.asu',
    'providers.edu.boisestate',
    'providers.edu.calhoun',
    'providers.edu.caltech',
    'providers.edu.chapman',
    'providers.edu.citeseerx',
    'providers.edu.cmu',
    'providers.edu.colostate',
    'providers.edu.columbia',
    'providers.edu.csuohio',
    'providers.edu.cuny',
    'providers.edu.cuscholar',
    'providers.edu.dash',
    'providers.edu.digitalhoward',
    'providers.edu.duke',
    'providers.edu.fit',
    'providers.edu.harvarddataverse',
    'providers.edu.huskiecommons',
    'providers.edu.iastate',
    'providers.edu.icpsr',
    'providers.edu.iowaresearch',
    'providers.edu.iu',
    'providers.edu.iwucommons',
    'providers.edu.kent',
    'providers.edu.krex',
    'providers.edu.mason',
    'providers.edu.mit',
    'providers.edu.mizzou',
    'providers.edu.nku',
    'providers.edu.oaktrust',
    'providers.edu.opensiuc',
    'providers.edu.pcom',
    'providers.et.edu.addisababa',
    'providers.gov.clinicaltrials',
    'providers.gov.doepages',
    'providers.gov.nih',
    'providers.gov.nist',
    'providers.gov.nodc',
    'providers.gov.nsfawards',
    'providers.io.osf',
    'providers.org.arxiv',
    'providers.org.arxiv.oai.apps.AppConfig',
    'providers.org.bhl',
    'providers.org.cogprints',
    'providers.org.crossref',
    'providers.org.datacite',
    'providers.org.dryad',
    'providers.org.elife',
    'providers.org.erudit',
    'providers.org.mblwhoilibrary',
    'providers.org.mla',
    'providers.org.ncar',
    'providers.org.neurovault',
    'providers.ru.cyberleninka',
    'providers.tr.edu.hacettepe',
    'providers.uk.cambridge',
    'providers.uk.lshtm',
    'providers.za.csir',
]

HARVESTER_SCOPES = 'upload_normalized_manuscript upload_raw_data'


OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'groups': 'Access to your groups',
        'upload_normalized_manuscript': 'Upload Normalized Manuscript',
        'upload_raw_data': 'Upload Raw Data'
    }
}

SOCIALACCOUNT_PROVIDERS = \
    {'osf':
         {
            'METHOD': 'oauth2',
            'SCOPE': ['osf.users.all_read'],
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
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': ('oauth2_provider.ext.rest_framework.OAuth2Authentication',),
    'PAGE_SIZE': 10,
    'DEFAULT_PARSER_CLASSES': (
        'api.parsers.JSONLDParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'api.renderers.JSONLDRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',)
}

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DATABASE_NAME', 'share'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
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

if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'allauth.account.auth_backends.AuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
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

STATIC_URL = '/static/'

ELASTIC_SEARCH_URI = os.environ.get('ELASTIC_SEARCH_URI', 'http://localhost:9200')
ELASTIC_SEARCH_INDEX = os.environ.get('ELASTIC_SEARCH_INDEX', 'share')

# Celery Settings

BROKER_URL = os.environ.get('BROKER_URL', 'amqp://'),

CELERY_TIMEZONE = 'UTC'
CELERYBEAT_SCHEDULE = {}

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_TRACK_STARTED = True
CELERY_RESULT_PERSISTENT = True
CELERY_SEND_EVENTS = True
CELERY_SEND_TASK_SENT_EVENT = True
CELERY_LOADER = 'djcelery.loaders.DjangoLoader'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

CELERY_IGNORE_RESULT = True
CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True

# Logging
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
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'console'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}


# Custom Settings

SHARE_API_URL = os.environ.get('SHARE_API_URL', 'http://localhost:8000').rstrip('/') + '/'
OSF_API_URL = os.environ.get('OSF_API_URL', 'https://staging-api.osf.io').rstrip('/') + '/'
SITE_ID = 1
DOI_BASE_URL = 'http://dx.doi.org/'
