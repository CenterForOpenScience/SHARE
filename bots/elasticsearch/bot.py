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

    SETTINGS = {
        'analysis': {
            'filter': {
                'autocomplete_filter': {
                    'type': 'edge_ngram',
                    'min_gram': 1,
                    'max_gram': 20
                }
            },
            'analyzer': {
                'default': {
                    # same as 'standard' analyzer, plus html_strip
                    'type': 'custom',
                    'tokenizer': 'standard',
                    'filter': ['lowercase', 'stop'],
                    'char_filter': ['html_strip']
                },
                'autocomplete': {
                    'type': 'custom',
                    'tokenizer': 'standard',
                    'filter': [
                        'lowercase',
                        'autocomplete_filter'
                    ]
                },
            }
        }
    }

    AUTOCOMPLETE_FIELD = {
        'autocomplete': {
            'type': 'string',
            'analyzer': 'autocomplete',
            'search_analyzer': 'standard',
            'include_in_all': False
        }
    }

    EXACT_FIELD = {
        'exact': {
            'type': 'string',
            'index': 'not_analyzed',
            # From Elasticsearch documentation:
            # The value for ignore_above is the character count, but Lucene counts bytes.
            # If you use UTF-8 text with many non-ASCII characters, you may want to set the limit to 32766 / 3 = 10922 since UTF-8 characters may occupy at most 3 bytes
            'ignore_above': 10922
        }
    }

    MAPPINGS = {
        'creativeworks': {
            'dynamic': False,
            'properties': {
                'affiliations': {'type': 'string', 'fields': EXACT_FIELD},
                'contributors': {'type': 'string', 'fields': EXACT_FIELD},
                'date': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_created': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_modified': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_published': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_updated': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'description': {'type': 'string'},
                'funders': {'type': 'string', 'fields': EXACT_FIELD},
                'hosts': {'type': 'string', 'fields': EXACT_FIELD},
                'id': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'identifiers': {'type': 'string', 'fields': EXACT_FIELD},
                'justification': {'type': 'string', 'include_in_all': False},
                'language': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'publishers': {'type': 'string', 'fields': EXACT_FIELD},
                'registration_type': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'retracted': {'type': 'boolean', 'include_in_all': False},
                'sources': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'subjects': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'tags': {'type': 'string', 'fields': EXACT_FIELD},
                'title': {'type': 'string'},
                'type': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'types': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'withdrawn': {'type': 'boolean', 'include_in_all': False},
                'lists': {'type': 'object', 'dynamic': True, 'include_in_all': False},
            },
            'dynamic_templates': [
                {'exact_field_on_lists_strings': {'path_match': 'lists.*', 'match_mapping_type': 'string', 'mapping': {'type': 'string', 'fields': EXACT_FIELD}}},
            ]
        },
        'agents': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'identifiers': {'type': 'string', 'fields': EXACT_FIELD},
                'name': {'type': 'string', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'family_name': {'type': 'string', 'include_in_all': False},
                'given_name': {'type': 'string', 'include_in_all': False},
                'additional_name': {'type': 'string', 'include_in_all': False},
                'suffix': {'type': 'string', 'include_in_all': False},
                'location': {'type': 'string', 'include_in_all': False},
                'sources': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'type': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'types': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
            }
        },
        'sources': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'name': {'type': 'string', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'short_name': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'type': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
            }
        },
        'tags': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
                'name': {'type': 'string', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'type': {'type': 'string', 'index': 'not_analyzed', 'include_in_all': False},
            }
        },
    }

    def __init__(self, config, started_by, last_run=None, es_url=None, es_index=None, es_setup=False):
        super().__init__(config, started_by, last_run=last_run)
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.es_index = es_index or settings.ELASTICSEARCH_INDEX
        self.es_client = Elasticsearch(self.es_url)
        self.es_setup = es_setup

    def run(self, chunk_size=500):
        if self.es_setup:
            self.setup()

        logger.info('Loading up indexed models')
        for model_name in self.config.INDEX_MODELS:
            model = apps.get_model('share', model_name)
            qs = model.objects.filter(date_modified__gt=self.last_run).values_list('id', flat=True)
            logger.info('Looking for %ss that have been modified after %s', model, self.last_run)

            logger.info('Found %s %s that must be updated in ES', qs.count(), model)
            for i, batch in enumerate(chunk(qs.all(), chunk_size)):
                IndexModelTask().apply_async((self.started_by.id, self.config.label, model.__name__, batch,), {'es_url': self.es_url, 'es_index': self.es_index})

        logger.info('Starting task to index sources')
        IndexSourceTask().apply_async((self.started_by.id, self.config.label), {'es_url': self.es_url, 'es_index': self.es_index})

    def setup(self):
        logger.debug('Ensuring Elasticsearch index %s', self.es_index)
        self.es_client.indices.create(self.es_index, ignore=400)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')

        logger.info('Putting Elasticsearch settings')
        self.es_client.indices.close(index=settings.ELASTICSEARCH_INDEX)
        try:
            self.es_client.indices.put_settings(body=self.SETTINGS, index=settings.ELASTICSEARCH_INDEX)
        finally:
            self.es_client.indices.open(index=settings.ELASTICSEARCH_INDEX)

        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in self.MAPPINGS.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=self.es_index
            )
