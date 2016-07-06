import logging

from django.conf import settings
from elasticsearch import helpers
from elasticsearch import Elasticsearch

from share.bot import Bot
from share.models import Person
from share.models import Association
from share.models import CeleryProviderTask
from share.models import AbstractCreativeWork

logger = logging.getLogger(__name__)


class ElasticSearchBot(Bot):

    INDEX_MODELS = [AbstractCreativeWork, Person]

    MAPPINGS = {
        'person': {
            'properties': {
                'sources': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
        'abstractcreativework': {
            'properties': {
                'sources': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    }

    def __init__(self, config):
        super().__init__(config)
        self.es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

    def serialize(self, inst):
        return {
            Person: self.serialize_person,
            AbstractCreativeWork: self.serialize_creative_work,
        }[type(inst)._meta.concrete_model](inst)

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
        # TODO Update format to whatever sharepa expects
        return {
            'title': creative_work.title,
            'associations': [entity.name for entity in Association.objects.select_related('entity').filter(creative_work=creative_work)],
            'awards': [str(award) for award in creative_work.awards.all()],
            'contributors': [self.serialize_person(person) for person in creative_work.contributors.all()],
            'date_created': creative_work.date_created.isoformat(),
            'description': creative_work.description,
            'language': creative_work.language,
            'links': [str(link) for link in creative_work.links.all()],
            'sources': [source.robot for source in creative_work.sources.all()],
            'subject': str(creative_work.subject),
            'tags': [str(tag) for tag in creative_work.tags.all()],
            'venues': [str(venue) for venue in creative_work.venues.all()],
        }

    def run(self, chunk_size=50, reindex_all=False):
        logger.debug('Ensuring Elasticsearch index %s', settings.ELASTICSEARCH_URL)
        self.es_client.indices.create(settings.ELASTICSEARCH_INDEX, ignore=400)

        self._put_mappings()

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

    def _put_mappings(self):
        logger.info('Putting Elasticsearch mappings')
        for doc_type, mapping in self.MAPPINGS.items():
            logger.debug('Putting mapping for %s', doc_type)
            self.es_client.indices.put_mapping(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=settings.ELASTICSEARCH_INDEX,
            )
