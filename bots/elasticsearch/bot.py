import logging

from django.conf import settings
from elasticsearch import helpers
from elasticsearch import Elasticsearch
from rest_framework.reverse import reverse

from share.bot import Bot
from share.models import Person
from share.models import Tag
from share.models import Entity
from share.models import Award
from share.models import Venue
from share.models import Association
from share.models import CeleryProviderTask
from share.models import AbstractCreativeWork

logger = logging.getLogger(__name__)


class ElasticSearchBot(Bot):

    INDEX_MODELS = [AbstractCreativeWork, Person]
    AUTO_COMPLETE_MODELS = [
        # (Model, attribute, )
        Person,
        Tag,
        Entity,
        Award,
        Venue
    ]

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

    def __init__(self, config, started_by):
        super().__init__(config, started_by)
        self.es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

    def serialize(self, inst):
        return {
            Person: self.serialize_person,
            AbstractCreativeWork: self.serialize_creative_work,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_autocomplete(self, model):
        return {
            '@id': str(model.pk),
            'text': str(model),
            '@type': type(model).__name__.lower(),
        }

    def serialize_person(self, person):
        return {
            'suffix': person.suffix,
            'given_name': person.given_name,
            'family_name': person.family_name,
            'full_name': person.get_full_name(),
            'additional_name': person.additional_name,
            'sources': [source.robot for source in person.sources.all()],
        }

    def serialize_creative_work(self, creative_work):
        return {
            '@type': type(creative_work).__name__.lower(),
            'title': creative_work.title,
            'associations': [association.entity.name for association in Association.objects.select_related('entity').filter(creative_work=creative_work)],
            'awards': [str(award) for award in creative_work.awards.all()],
            'contributors': [self.serialize_person(person) for person in creative_work.contributors.all()],
            'date_created': creative_work.date_created.isoformat(),
            'date_modified': creative_work.date_modified.isoformat(),
            'date': (creative_work.date_published or creative_work.date_updated or creative_work.date_created).isoformat(),
            'description': creative_work.description,
            'language': creative_work.language,
            'links': [str(link) for link in creative_work.links.all()],
            'sources': [source.robot for source in creative_work.sources.all()],
            'subject': str(creative_work.subject),
            'tags': [str(tag) for tag in creative_work.tags.all()],
            'venues': [str(venue) for venue in creative_work.venues.all()],
        }

    def run(self, last_run, chunk_size=50, reindex_all=False):
        self._setup()

        logger.debug('Finding last successful job')
        last_run = CeleryProviderTask.objects.filter(
            app_label=self.config.label,
            app_version=self.config.version,
            status=CeleryProviderTask.STATUS.succeeded,
        ).order_by(
            '-timestamp'
        ).first()

        if last_run:
            logger.info('Found last job %s', last_run)
            last_run = last_run.timestamp

        for model in self.INDEX_MODELS:
            for resp in helpers.streaming_bulk(self.es_client, self.bulk_stream(model, last_run)):
                logger.debug(resp)

        logger.info('Loading up autocomplete type')
        for model in self.AUTO_COMPLETE_MODELS:
            for resp in helpers.streaming_bulk(self.es_client, self.bulk_stream_autocomplete(model, cutoff_date=last_run)):
                logger.debug(resp)

    def bulk_stream(self, model, cutoff_date=None):
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': model.__name__.lower()}

        if cutoff_date:
            qs = model.objects.filter(date_modified__gt=cutoff_date)
            logger.info('Looking for %ss that have been modified after %s', model, cutoff_date)
        else:
            qs = model.objects.all()
            logger.info('Getting all %s', model)

        logger.info('Found %s %s that must be updated in ES', qs.count(), model)

        for inst in qs:
            yield {'_id': inst.pk, '_op_type': 'index', **self.serialize(inst), **opts}
            # if acw.is_delete:  # TODO
            #     yield {'_id': acw.pk, '_op_type': 'delete', **opts}

    def bulk_stream_autocomplete(self, model, cutoff_date=None):
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': 'autocomplete'}

        if cutoff_date:
            qs = model.objects.filter(date_modified__gt=cutoff_date)
            logger.info('Looking for %ss that have been modified after %s', model, cutoff_date)
        else:
            qs = model.objects.all()
            logger.info('Getting all %s', model)

        logger.info('Found %s %s that must be updated in ES', qs.count(), model)

        for inst in qs:
            yield {
                '_op_type': 'index',
                '_id': reverse('api:{}-detail'.format(model._meta.model_name), (inst.pk,)),
                **self.serialize_autocomplete(inst),
                **opts
            }

    def _setup(self):
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
