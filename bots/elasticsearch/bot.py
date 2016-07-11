import logging

from django.conf import settings
from django.db import transaction
from elasticsearch import helpers
from elasticsearch import Elasticsearch
from rest_framework.reverse import reverse

from db.backends.postgresql.base import server_side_cursors
from share.bot import Bot
from share.models import Person
from share.models import Tag
from share.models import Entity
from share.models import Award
from share.models import Venue
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

    def __init__(self, config, started_by, last_run=None):
        super().__init__(config, started_by, last_run=last_run)
        self.es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

    def serialize(self, inst):
        return {
            Person: self.serialize_person,
            AbstractCreativeWork: self.serialize_creative_work,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_autocomplete(self, model):
        return {
            '@id': str(model.pk),
            'text': str(model)[:32766],
            '@type': type(model).__name__.lower(),
        }

    def serialize_person(self, person):
        return {
            '@id': person.pk,
            '@type': 'person',
            'suffix': person.suffix[:32766],
            'given_name': person.given_name[:32766],
            'family_name': person.family_name[:32766],
            'full_name': person.get_full_name()[:32766],
            'additional_name': person.additional_name[:32766],
            'identifiers': [{
                                'url': identifier.url,
                                'base_url': identifier.base_url,
                            } for identifier in person.identifiers.all()],
            'affiliations': [
                self.serialize_entity(affiliation)
                for affiliation in
                person.affiliations.all()
                ],
            'sources': [source.robot for source in person.sources.all()],
        }

    def serialize_entity(self, entity):
        return {
            '@id': entity.pk,
            'name': entity.name[:32766],
            '@type': type(entity).__name__.lower(),
        }

    def serialize_creative_work(self, creative_work):
        return {
            '@type': type(creative_work).__name__.lower(),
            'associations': [
                self.serialize_entity(association)
                for association in
                [
                    *creative_work.funders.all(),
                    *creative_work.publishers.all(),
                    *creative_work.institutions.all(),
                    *creative_work.organizations.all()
                ]
                ],
            'title': creative_work.title[:32766],
            'language': creative_work.language[:32766],
            'subject': str(creative_work.subject),
            'description': creative_work.description[:32766],
            'date': (
            creative_work.date_published or creative_work.date_updated or creative_work.date_created).isoformat(),
            'date_created': creative_work.date_created.isoformat(),
            'date_modified': creative_work.date_modified.isoformat(),
            'date_updated': creative_work.date_updated.isoformat() if creative_work.date_updated else None,
            'date_published': creative_work.date_published.isoformat() if creative_work.date_published else None,
            'tags': [str(tag)[:32766] for tag in creative_work.tags.all()],
            'links': [str(link)[:32766] for link in creative_work.links.all()],
            'awards': [str(award)[:32766] for award in creative_work.awards.all()],
            'venues': [str(venue)[:32766] for venue in creative_work.venues.all()],
            'sources': [source.robot for source in creative_work.sources.all()],
            'contributors': [self.serialize_person(person) for person in creative_work.contributors.all()],
        }

    def run(self, chunk_size=50, reindex_all=False):
        self._setup()

        for model in self.INDEX_MODELS:
            for resp in helpers.streaming_bulk(self.es_client, self.bulk_stream(model, self.last_run.datetime)):
                logger.debug(resp)

        logger.info('Loading up autocomplete type')
        for model in self.AUTO_COMPLETE_MODELS:
            for resp in helpers.streaming_bulk(self.es_client,
                                               self.bulk_stream_autocomplete(model, cutoff_date=self.last_run.datetime)):
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
        with transaction.atomic():
            with server_side_cursors(qs):
                for inst in qs.iterator():
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
        with transaction.atomic():
            with server_side_cursors(qs):
                for inst in qs.iterator():
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
