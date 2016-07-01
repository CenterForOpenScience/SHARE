import logging

from django.conf import settings
from elasticsearch import helpers
from elasticsearch import Elasticsearch

from share.bot import Bot
from share.models import CeleryProviderTask
from share.models import AbstractCreativeWork

logger = logging.getLogger(__name__)


class ElasticSearchBot(Bot):

    def __init__(self, config):
        super().__init__(config)
        self.es_client = Elasticsearch(settings.ELASTIC_SEARCH_URI)

    def serialize(self, creative_work):
        # TODO Update format to whatever sharepa expects
        return {
            'doi': creative_work.doi,
            'title': creative_work.title,
            'description': creative_work.description,
            'contributors': [{
                'given_name': person.given_name,
                'family_name': person.family_name,
            } for person in creative_work.contributors.all()]
        }

    def run(self, chunk_size=50, reindex_all=False):
        # TODO Filter on task succeeded
        last_run = CeleryProviderTask.objects.filter(
            app_label=self.config.label
        ).order_by(
            '-date_created'
        ).first()

        if last_run:
            last_run = last_run.date_created

        last_run = None

        for resp in helpers.streaming_bulk(self.es_client, self.bulk_stream(last_run)):
            logger.debug(resp)

    def bulk_stream(self, cutoff_date=None):
        opts = {'_index': settings.ELASTIC_SEARCH_INDEX, '_type': 'document'}

        if cutoff_date:
            qs = AbstractCreativeWork.objects.filter(date_modified__gt=cutoff_date)
        else:
            qs = AbstractCreativeWork.objects.all()

        logger.info('Found %s creative works that must be updated in ES', qs.count())

        for acw in qs:
            yield {'_id': acw.pk, '_op_type': 'index', 'doc': self.serialize(acw), **opts}
            # if acw.is_delete:  # TODO
            #     yield {'_id': acw.pk, '_op_type': 'delete', **opts}
