import logging

import celery

from django.db.models import Exists
from django.db.models import OuterRef

from raven.contrib.django.raven_compat.models import client

from share import tasks
from share.models import NormalizedData
from share.models import RawDatum


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True)
def rawdata_janitor(self, limit=500):
    """Find RawDatum that do not have a NormalizedData process them
    """
    count = 0

    # NOTE: Do NOT use .iterator here. It will create a temporary table and eat disk space like no other
    # the limit lets this query fit nicely in memory and actually finish executing
    # Be very careful about changing this query. If you do change it, make sure the EXPLAIN looks something like this:
    # Limit  (cost=1.13..Much Smaller Numbers)
    #   ->  Nested Loop  (cost=1.13..Big Numbers)
    #         Join Filter: (share_sourceuniqueidentifier.source_config_id = share_sourceconfig.id)
    #         ->  Nested Loop  (cost=1.13..Big Numbers)
    #               ->  Nested Loop Anti Join  (cost=0.56..Big Numbers)
    #                     ->  Seq Scan on share_rawdatum  (cost=0.00..Big Numbers)
    #                     ->  Index Only Scan using share_normalizeddata_c0e72696 on share_normalizeddata  (cost=0.56..Small Numbers)
    #                           Index Cond: (raw_id = share_rawdatum.id)

    qs = RawDatum.objects.select_related('suid__source_config').annotate(
        has_normalizedata=Exists(NormalizedData.objects.values('id').filter(raw=OuterRef('id'))),
    ).exclude(no_output=True).exclude(has_normalizedata=True)

    for rd in qs[:limit]:
        count += 1
        logger.debug('Found unprocessed %r from %r', rd, rd.suid.source_config)
        try:
            t = tasks.transform.apply((rd.id, ), throw=True, retries=tasks.transform.max_retries + 1)
        except Exception as e:
            client.captureException()
            logger.exception('Failed to processed %r', rd)
        else:
            logger.info('Processed %r via %r', rd, t)
    if count:
        logger.warning('Found %d total unprocessed RawData', count)
    return count
