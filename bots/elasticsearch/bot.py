import logging

import itertools
from django.apps import apps
from django.conf import settings
from elasticsearch import Elasticsearch

from bots.elasticsearch.tasks import IndexModelTask
from bots.elasticsearch.tasks import IndexAutoCompleteTask
from share.bot import Bot

logger = logging.getLogger(__name__)


def chunk(iterable, size):
    iterable = iter(iterable)
    try:
        while True:
            l = []
            for _ in range(size):
                l.append(next(iterable))
            yield l
    except StopIteration:
        yield l


class ElasticSearchBot(Bot):

    SETTINGS = {
        'analysis': {
            'filter': {
                'autocomplete_filter': {
                    'type': 'edge_ngram',
                }
            },
            'analyzer': {
                'autocomplete': {
                    'type': 'custom',
                    'tokenizer': 'standard',
                    'filter': ['lowercase', 'autocomplete_filter']
                }
            }
        }
    }

    MAPPINGS = {
        'autocomplete': {
            'properties': {
                '@id': {
                    'type': 'string',
                    'index': 'not_analyzed'
                },
                '@type': {
                    'type': 'string',
                    'index': 'not_analyzed'
                },
                'text': {
                    'type': 'string',
                    'analyzer': 'autocomplete'
                }
            }
        },
        'person': {
            'properties': {
                'sources': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
        'abstractcreativework': {
            'dynamic_templates': [{
                'exact_matches': {
                    'unmatch': 'description',
                    'match_mapping_type': 'string',
                    'mapping': {
                        'type': 'string',
                        'fields': {
                            'raw': {'type': 'string', 'index': 'not_analyzed'}
                        }
                    }
                }
            }],
            'properties': {
                'sources': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    }

    def __init__(self, config, started_by, last_run=None):
        super().__init__(config, started_by, last_run=last_run)
        self.es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

    def run(self, chunk_size=500):
        self.setup()

        logger.info('Loading up indexed models')
        for model_name in self.config.INDEX_MODELS:
            model = apps.get_model('share', model_name)
            qs = model.objects.filter(date_modified__gt=self.last_run.datetime).values_list('id', flat=True)
            logger.info('Looking for %ss that have been modified after %s', model, self.last_run.datetime)

            logger.info('Found %s %s that must be updated in ES', qs.count(), model)
            for i, batch in enumerate(chunk(qs.all(), chunk_size)):
                IndexModelTask().apply_async((self.config.label, self.started_by.id, model.__name__, batch,))

        logger.info('Loading up autocomplete models')
        for model_name in self.config.AUTO_COMPLETE_MODELS:
            model = apps.get_model('share', model_name)
            qs = model.objects.filter(date_modified__gt=self.last_run.datetime).values_list('id', flat=True)
            logger.info('Looking for %ss that have been modified after %s', model, self.last_run.datetime)

            logger.info('Found %s %s that must be updated in ES', qs.count(), model)
            for i, batch in enumerate(chunk(qs.all(), chunk_size)):
                IndexAutoCompleteTask().apply_async((self.config.label, self.started_by.id, model.__name__, batch,))

    def setup(self):
        logger.debug('Ensuring Elasticsearch index %s', settings.ELASTICSEARCH_INDEX)
        self.es_client.indices.create(settings.ELASTICSEARCH_INDEX, ignore=400)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')

        logger.debug('Closing index %s', settings.ELASTICSEARCH_INDEX)
        self.es_client.indices.close(index=settings.ELASTICSEARCH_INDEX)

        logger.debug('Update Elasticsearch settings')
        self.es_client.indices.put_settings({'settings': self.SETTINGS}, index=settings.ELASTICSEARCH_INDEX)

        logger.debug('Open index %s', settings.ELASTICSEARCH_INDEX)
        self.es_client.indices.open(index=settings.ELASTICSEARCH_INDEX)

        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in self.MAPPINGS.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=settings.ELASTICSEARCH_INDEX,
            )
