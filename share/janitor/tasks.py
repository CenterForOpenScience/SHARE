import logging

import celery

from share import tasks
from share.models import RawDatum


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True)
def rawdata_janitor(self, limit=100):
    """Find RawDatum that do not have a NormalizedData process them
    """
    count = 0
    for rd in RawDatum.objects.select_related('suid__source_config').filter(normalizeddata__isnull=True).order_by('id')[:limit].iterator():
        count += 1
        logger.debug('Found unprocessed %r from %r', rd, rd.suid.source_config)
        try:
            t = tasks.transform.apply((rd.id, ), throw=True, retries=tasks.transform.max_retries + 1)
        except Exception as e:
            logger.exception('Failed to processed %r via %r', rd, t)
        else:
            logger.info('Processed %r via %r', rd, t)
    if count:
        logger.warning('Found %d total unprocessed RawData', count)
    return count
