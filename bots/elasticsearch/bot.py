import logging

from django.conf import settings
from elasticsearch import helpers
from elasticsearch import Elasticsearch

from share.bot import Bot
from share.models import AbstractCreativeWork
from share.models import CeleryProviderTask

logger = logging.getLogger(__name__)


class ElasticSearchBot(Bot):

    def __init__(self, config):
        super().__init__(config)
        self.es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

    def serialize(self, creative_work):
        # TODO Update format to whatever sharepa expects
        return {
            'doi': creative_work.doi,
            'title': creative_work.title,
            'subject': str(creative_work.subject),
            'description': creative_work.description,
            'tags': [str(tag) for tag in creative_work.tags],
            'contributors': [{
                'given_name': person.given_name,
                'family_name': person.family_name,
            } for person in creative_work.contributors.all()]
        }

    def run(self, chunk_size=50, reindex_all=False):
        last_run = CeleryProviderTask.objects.filter(
            app_label=self.config.label,
            app_version=self.config.version,
            status=CeleryProviderTask.STATUS.succeeded,
        ).order_by(
            '-timestamp'
        ).first()

        if last_run:
            last_run = last_run.timestamp

        for resp in helpers.streaming_bulk(self.es_client, self.bulk_stream(last_run)):
            logger.debug(resp)

    def bulk_stream(self, cutoff_date=None):
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': 'document'}

        if cutoff_date:
            qs = AbstractCreativeWork.objects.filter(date_modified__gt=cutoff_date)
            logger.info('Looking for Creative Works that have been modified after %s', cutoff_date)
        else:
            qs = AbstractCreativeWork.objects.all()
            logger.info('Getting all Creative Works')

        logger.info('Found %s creative works that must be updated in ES', qs.count())

        for acw in qs:
            yield {'_id': acw.pk, '_op_type': 'index', 'doc': self.serialize(acw), **opts}
            # if acw.is_delete:  # TODO
            #     yield {'_id': acw.pk, '_op_type': 'delete', **opts}
