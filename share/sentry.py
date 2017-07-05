import logging

import raven

from django.conf import settings


logger = logging.getLogger(__name__)


if hasattr(settings, 'RAVEN_CONFIG') and settings.RAVEN_CONFIG['dsn']:
    logger.info('Sentry is active')
    sentry_client = raven.Client(settings.RAVEN_CONFIG['dsn'])
else:
    # If dsn is None all raven/sentry calls become NOOPs
    logger.info('Sentry is NOT active')
    sentry_client = raven.Client(dsn=None)
