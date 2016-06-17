import warnings

from logging.config import dictConfig
from django.utils.deprecation import RemovedInDjango110Warning


# Source: http://stackoverflow.com/a/34696433
IGNORE_DJANGO_110_WARNINGS = {
    r'six': r'SubfieldBase has been deprecated.*',
    r'enumfields\.fields': r'SubfieldBase has been deprecated.*'
}


def configure(settings):
    dictConfig(settings)
    for module, message in IGNORE_DJANGO_110_WARNINGS.items():
        warnings.filterwarnings(
            action='ignore', category=RemovedInDjango110Warning, module=module, message=message
    )
