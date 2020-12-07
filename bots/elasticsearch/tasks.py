import logging

import celery

from django.apps import apps
from django.conf import settings

from elasticsearch import Elasticsearch
from elasticsearch import helpers


logger = logging.getLogger(__name__)


def safe_substr(value, length=32000):
    if value:
        return str(value)[:length]
    return None


@celery.shared_task(bind=True)
def index_sources(self, es_index=None, es_url=None, timeout=None):
    errors = []
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH['URL'], retry_on_timeout=True, timeout=settings.ELASTICSEARCH['TIMEOUT'])

    for ok, resp in helpers.streaming_bulk(es_client, SourceBulkStreamHelper(es_index or settings.ELASTICSEARCH['PRIMARY_INDEX']), raise_on_error=False):
        if not ok:
            logger.warning(resp)
        else:
            logger.debug(resp)

        if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
            errors.append(resp)

    if errors:
        raise Exception('Failed to index documents {}'.format(errors))


class SourceBulkStreamHelper:

    def __init__(self, es_index):
        self.es_index = es_index

    def __iter__(self):
        Source = apps.get_model('share.Source')
        opts = {'_index': self.es_index, '_type': 'sources'}

        for source in Source.objects.all():
            # remove sources from search that don't appear on the sources page
            if not source.icon or source.is_deleted:
                yield {'_op_type': 'delete', '_id': source.name, **opts}
            else:
                yield {'_op_type': 'index', '_id': source.name, **self.serialize(source), **opts}

    def serialize(self, source):
        return {
            'id': source.name,
            'type': 'source',
            'name': safe_substr(source.long_title),
            'short_name': safe_substr(source.name)
        }
