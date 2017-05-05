import logging
import pendulum

from django.apps import apps
from django.conf import settings
from elasticsearch import Elasticsearch

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


class ElasticSearchBot:

    # Sources are also indexed as a special case
    INDEX_MODELS = [
        'CreativeWork',
        'Agent',
        'Tag',
        # 'Subject',
    ]

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
            'type': 'keyword',
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
                'affiliations': {'type': 'text', 'fields': EXACT_FIELD},
                'contributors': {'type': 'text', 'fields': EXACT_FIELD},
                'date': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_created': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_modified': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_published': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_updated': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'description': {'type': 'text'},
                'funders': {'type': 'text', 'fields': EXACT_FIELD},
                'hosts': {'type': 'text', 'fields': EXACT_FIELD},
                'id': {'type': 'keyword', 'include_in_all': False},
                'identifiers': {'type': 'text', 'fields': EXACT_FIELD},
                'justification': {'type': 'text', 'include_in_all': False},
                'language': {'type': 'keyword', 'include_in_all': False},
                'publishers': {'type': 'text', 'fields': EXACT_FIELD},
                'registration_type': {'type': 'keyword', 'include_in_all': False},
                'retracted': {'type': 'boolean', 'include_in_all': False},
                'sources': {'type': 'keyword', 'include_in_all': False},
                'subjects': {'type': 'keyword', 'include_in_all': False},
                'tags': {'type': 'text', 'fields': EXACT_FIELD},
                'title': {'type': 'text', 'fields': EXACT_FIELD},
                'type': {'type': 'keyword', 'include_in_all': False},
                'types': {'type': 'keyword', 'include_in_all': False},
                'withdrawn': {'type': 'boolean', 'include_in_all': False},
                'lists': {'type': 'object', 'dynamic': True, 'include_in_all': False},
            },
            'dynamic_templates': [
                {'exact_field_on_lists_strings': {'path_match': 'lists.*', 'match_mapping_type': 'string', 'mapping': {'type': 'text', 'fields': EXACT_FIELD}}},
            ]
        },
        'agents': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'keyword', 'include_in_all': False},
                'identifiers': {'type': 'text', 'fields': EXACT_FIELD},
                'name': {'type': 'text', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'family_name': {'type': 'text', 'include_in_all': False},
                'given_name': {'type': 'text', 'include_in_all': False},
                'additional_name': {'type': 'text', 'include_in_all': False},
                'suffix': {'type': 'text', 'include_in_all': False},
                'location': {'type': 'text', 'include_in_all': False},
                'sources': {'type': 'keyword', 'include_in_all': False},
                'type': {'type': 'keyword', 'include_in_all': False},
                'types': {'type': 'keyword', 'include_in_all': False},
            }
        },
        'sources': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'keyword', 'include_in_all': False},
                'name': {'type': 'text', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'short_name': {'type': 'keyword', 'include_in_all': False},
                'type': {'type': 'keyword', 'include_in_all': False},
            }
        },
        'tags': {
            'dynamic': False,
            'properties': {
                'id': {'type': 'keyword', 'include_in_all': False},
                'name': {'type': 'text', 'fields': {**AUTOCOMPLETE_FIELD, **EXACT_FIELD}},
                'type': {'type': 'keyword', 'include_in_all': False},
            }
        },
    }

    def __init__(self, **kwargs):
        self.es_filter = kwargs.pop('es_filter', None)
        self.es_index = kwargs.pop('es_index', settings.ELASTICSEARCH_INDEX)
        self.es_models = kwargs.pop('es_models', None)
        self.es_setup = bool(kwargs.pop('es_setup', False))
        self.es_url = kwargs.pop('es_url', settings.ELASTICSEARCH_URL)

        if self.es_models:
            self.es_models = [x.lower() for x in self.es_models]

        if kwargs:
            raise TypeError('__init__ got unexpect keyword arguments {}'.format(kwargs))

        self.es_client = Elasticsearch(self.es_url)

    def get_most_recently_modified(self):
        resp = self.es_client.search(
            index=(self.es_index or settings.ELASTICSEARCH_INDEX),
            doc_type='creativeworks',
            body='{"sort": {"date_modified": "desc"}, "size": 1}'
        )
        if resp['hits']['hits']:
            return resp['hits']['hits'][0]['_source']['date_modified']
        return '2000-01-01T00:00:00-00:00'

    def run(self, chunk_size=500):
        from bots.elasticsearch import tasks  # TODO fix me

        if self.es_setup:
            self.setup()
        else:
            logger.debug('Skipping ES setup')

        logger.info('Loading up indexed models')
        for model_name in self.INDEX_MODELS:
            if self.es_models and model_name.lower() not in self.es_models:
                continue

            model = apps.get_model('share', model_name)

            if self.es_filter:
                logger.info('Looking for %ss that match %s', model, self.es_filter)
                qs = model.objects.filter(**self.es_filter).values_list('id', flat=True)
            else:
                most_recent_result = pendulum.parse(self.get_most_recently_modified())
                logger.info('Looking for %ss that have been modified after %s', model, most_recent_result)
                qs = model.objects.filter(date_modified__gt=most_recent_result).values_list('id', flat=True)

            count = qs.count()

            if count < 1:
                logger.info('Found 0 qualifying %ss', model)
                continue
            else:
                logger.info('Found %s %s that must be updated in ES', count, model)

            for i, batch in enumerate(chunk(qs.all(), chunk_size)):
                if batch:
                    tasks.index_model.apply_async((model.__name__, batch,), {'es_url': self.es_url, 'es_index': self.es_index})

        logger.info('Starting task to index sources')
        tasks.index_sources.apply_async((), {'es_url': self.es_url, 'es_index': self.es_index})

    def setup(self):
        logger.debug('Ensuring Elasticsearch index %s', self.es_index)
        self.es_client.indices.create(self.es_index, ignore=400)

        logger.debug('Waiting for yellow status')
        self.es_client.cluster.health(wait_for_status='yellow')

        logger.info('Putting Elasticsearch settings')
        self.es_client.indices.close(index=self.es_index)
        try:
            self.es_client.indices.put_settings(body=self.SETTINGS, index=self.es_index)
        finally:
            self.es_client.indices.open(index=self.es_index)

        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in self.MAPPINGS.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=self.es_index
            )
