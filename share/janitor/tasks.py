import logging

import celery

from share import tasks
from share.models import RawDatum


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True)
def rawdata_janitor(self, limit=500):
    """Find RawDatum that do not have a NormalizedData process them
    """
    count = 0
    for rd in RawDatum.objects.select_related('suid__source_config').filter(normalizeddata__isnull=True).order_by('id')[:limit]:
        count += 1
        logger.debug('Found unprocessed %r from %r', rd, rd.suid.source_config)
        t = tasks.transform.apply((rd.id, ))
        logger.info('Processed %r via %r', rd, t)
    if count:
        logger.warning('Found %d total unprocessed RawData', count)
    return count
