from .utils import root

STATIC_ROOT = root('static_media', 'static_root')
STATIC_URL = '/media/static/'

STATICFILES_DIRS = (
    root('static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
