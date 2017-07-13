import logging
import random

import celery

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import transaction

from share.change import ChangeGraph
from share.harvest.scheduler import HarvestScheduler
from share.models import AbstractCreativeWork
from share.models import ChangeSet
from share.models import HarvestJob
from share.models import NormalizedData
from share.models import Source
from share.models import SourceConfig
from share.search import SearchIndexer
from share.tasks.jobs import HarvestJobConsumer
from share.tasks.jobs import IngestJobConsumer
from share.util.source_stat import SourceStatus
from share.util.source_stat import OAISourceStatus


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True, max_retries=5)
def disambiguate(self, normalized_id):
    normalized = NormalizedData.objects.select_related('source__source').get(pk=normalized_id)

    if self.request.id:
        self.update_state(meta={
            'source': normalized.source.source.long_title
        })

    updated = None

    try:
        # Load all relevant ContentTypes in a single query
        ContentType.objects.get_for_models(*apps.get_models('share'), for_concrete_models=False)

        with transaction.atomic():
            cg = ChangeGraph(normalized.data['@graph'], namespace=normalized.source.username)
            cg.process()
            cs = ChangeSet.objects.from_graph(cg, normalized.id)
            if cs and (normalized.source.is_robot or normalized.source.is_trusted or Source.objects.filter(user=normalized.source).exists()):
                # TODO: verify change set is not overwriting user created object
                updated = cs.accept()
    except Exception as e:
        raise self.retry(
            exc=e,
            countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 15)
        )

    if not updated:
        return
    # Only index creativeworks on the fly, for the moment.
    updated_works = set(x.id for x in updated if isinstance(x, AbstractCreativeWork))
    existing_works = set(n.instance.id for n in cg.nodes if isinstance(n.instance, AbstractCreativeWork))
    ids = list(updated_works | existing_works)

    try:
        SearchIndexer(self.app).index('creativework', *ids)
    except Exception as e:
        logger.exception('Could not add results from %r to elasticqueue', normalized)
        raise


@celery.shared_task(bind=True)
def schedule_harvests(self, *source_config_ids, cutoff=None):
    """

    Args:
        *source_config_ids (int): PKs of the source configs to schedule harvests for.
            If omitted, all non-disabled and non-deleted source configs will be scheduled
        cutoff (optional, datetime): The time to schedule harvests up to. Defaults to today.

    """
    if source_config_ids:
        qs = SourceConfig.objects.filter(id__in=source_config_ids)
    else:
        qs = SourceConfig.objects.exclude(disabled=True).exclude(source__is_deleted=True)

    with transaction.atomic():
        jobs = []

        # TODO take harvest/sourceconfig version into account here
        for source_config in qs.exclude(harvester__isnull=True).select_related('harvester').annotate(latest=models.Max('harvestjobs__end_date')):
            jobs.extend(HarvestScheduler(source_config).all(cutoff=cutoff, save=False))

        HarvestJob.objects.bulk_get_or_create(jobs)


@celery.shared_task(bind=True, max_retries=5)
def harvest(self, **kwargs):
    """Complete the harvest of the given HarvestJob or the next available HarvestJob.

    Keyword arguments from JobConsumer.consume, plus:
        ingest (bool, optional): Whether or not to start the full ingest process for harvested data. Defaults to True.
        limit (int, optional): Maximum number of data to harvest. Defaults to no limit.
    """
    HarvestJobConsumer(self).consume(**kwargs)


@celery.shared_task(bind=True, max_retries=5)
def ingest(self, **kwargs):
    """Ingest the data of the given IngestJob or the next available IngestJob.

    Keyword arguments from JobConsumer.consume
    """
    IngestJobConsumer(self).consume(**kwargs)


@celery.shared_task(bind=True)
def source_stats(self):
    oai_sourceconfigs = SourceConfig.objects.filter(
        disabled=False,
        base_url__isnull=False,
        harvester__key='oai'
    )
    for config in oai_sourceconfigs.values():
        get_source_stats.apply_async((config['id'],))

    non_oai_sourceconfigs = SourceConfig.objects.filter(
        disabled=False,
        base_url__isnull=False
    ).exclude(
        harvester__key='oai'
    )
    for config in non_oai_sourceconfigs.values():
        get_source_stats.apply_async((config['id'],))


@celery.shared_task(bind=True)
def get_source_stats(self, config_id):
    source_config = SourceConfig.objects.get(pk=config_id)
    if source_config.harvester.key == 'oai':
        OAISourceStatus(config_id).get_source_stats()
    else:
        SourceStatus(config_id).get_source_stats()
