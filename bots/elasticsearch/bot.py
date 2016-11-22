import logging

from django.apps import apps
from django.conf import settings
from elasticsearch import Elasticsearch

from bots.elasticsearch.tasks import IndexModelTask
from bots.elasticsearch.tasks import IndexSourceTask
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

    SUGGEST_MAPPING = {
        'type': 'completion',
        'payloads': True,
        'context': {
            'types': {
                'type': 'category',
                'path': 'types'
            }
        }
    }

    MAPPINGS = {
        'creativeworks': {
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
            }, {
                'exact_matches': {
                    'match': 'id',
                    'mapping': {
                        'enabled': False
                    }
                }
            }],
            'properties': {
                'tags': {
                    'type': {'type': 'string', 'index': 'not_analyzed'}
                },
                'subjects': {
                    'type': {'type': 'string', 'index': 'not_analyzed'}
                }
            }
        },
        'agents': {
            'properties': {
                'suggest': SUGGEST_MAPPING
            }
        },
        'sources': {
            'properties': {
                'suggest': SUGGEST_MAPPING
            }
        },
        'tags': {
            'properties': {
                'suggest': SUGGEST_MAPPING
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
            qs = model.objects.filter(date_modified__gt=self.last_run).values_list('id', flat=True)
            logger.info('Looking for %ss that have been modified after %s', model, self.last_run)

            logger.info('Found %s %s that must be updated in ES', qs.count(), model)
            for i, batch in enumerate(chunk(qs.all(), chunk_size)):
                IndexModelTask().apply_async((self.config.label, self.started_by.id, model.__name__, batch,))

        logger.info('Starting task to index sources')
        IndexSourceTask().apply_async((self.config.label, self.started_by.id))

    def setup(self):
        logger.debug('Ensuring Elasticsearch index %s', settings.ELASTICSEARCH_INDEX)
        self.es_client.indices.create(settings.ELASTICSEARCH_INDEX, ignore=400)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')

        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in self.MAPPINGS.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=settings.ELASTICSEARCH_INDEX,
            )
