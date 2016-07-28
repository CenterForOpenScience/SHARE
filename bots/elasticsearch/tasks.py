import logging

from django.apps import apps
from elasticsearch import helpers
from elasticsearch import Elasticsearch

from project import settings

from share.tasks import ProviderTask
from share.models import AbstractCreativeWork
from share.models import Person

logger = logging.getLogger(__name__)


def safe_substr(value, length=32000):
    if value:
        return str(value)[:length]
    return None


class IndexModelTask(ProviderTask):

    def do_run(self, model_name, ids):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
        model = apps.get_model('share', model_name)
        for resp in helpers.streaming_bulk(es_client, self.bulk_stream(model, ids)):
            logger.debug(resp)

    def bulk_stream(self, model, ids):
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': model.__name__.lower()}
        qs = model.objects.filter(id__in=ids)
        for inst in qs.all():
            # if inst.is_delete:  # TODO
            #     yield {'_id': inst.pk, '_op_type': 'delete', **opts}
            yield {'_id': inst.pk, '_op_type': 'index', **self.serialize(inst), **opts}

    def serialize(self, inst):
        return {
            Person: self.serialize_person,
            AbstractCreativeWork: self.serialize_creative_work,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_person(self, person):
        return {
            '@id': person.pk,
            '@type': 'person',
            'suffix': safe_substr(person.suffix),
            'given_name': safe_substr(person.given_name),
            'family_name': safe_substr(person.family_name),
            'full_name': safe_substr(person.get_full_name()),
            'additional_name': safe_substr(person.additional_name),
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
            'name': safe_substr(entity.name),
            '@type': type(entity).__name__.lower(),
        }

    def serialize_creative_work(self, creative_work):
        return {
            '@type': type(creative_work).__name__.lower(),
            'associations': [
                self.serialize_entity(association)
                for association in [
                    *creative_work.funders.all(),
                    *creative_work.publishers.all(),
                    *creative_work.institutions.all(),
                    *creative_work.organizations.all()
                ]
            ],
            'title': safe_substr(creative_work.title),
            'language': safe_substr(creative_work.language),
            'subject': safe_substr(creative_work.subject),
            'description': safe_substr(creative_work.description),
            'date': (
                creative_work.date_published or creative_work.date_updated or creative_work.date_created
            ).isoformat(),
            'date_created': creative_work.date_created.isoformat(),
            'date_modified': creative_work.date_modified.isoformat(),
            'date_updated': creative_work.date_updated.isoformat() if creative_work.date_updated else None,
            'date_published': creative_work.date_published.isoformat() if creative_work.date_published else None,
            'tags': [safe_substr(tag) for tag in creative_work.tags.all()],
            'links': [safe_substr(link) for link in creative_work.links.all()],
            'awards': [safe_substr(award) for award in creative_work.awards.all()],
            'venues': [safe_substr(venue) for venue in creative_work.venues.all()],
            'sources': [source.robot for source in creative_work.sources.all()],
            'contributors': [self.serialize_person(person) for person in creative_work.contributors.all()],
        }


class IndexAutoCompleteTask(ProviderTask):

    def do_run(self, model_name, ids):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
        model = apps.get_model('share', model_name)
        for resp in helpers.streaming_bulk(es_client, self.bulk_stream(model, ids)):
            logger.debug(resp)

    def bulk_stream(self, model, ids):
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': 'autocomplete'}
        qs = model.objects.filter(id__in=ids)
        for inst in qs.all():
            # if inst.is_delete:  # TODO
            #     yield {'_id': inst.pk, '_op_type': 'delete', **opts}
            yield {'_op_type': 'index', '_id': inst.uuid, **self.serialize(inst), **opts}

    def serialize(self, model):
        return {
            '@id': str(model.pk),
            'text': safe_substr(model),
            '@type': type(model).__name__.lower(),
        }


class IndexProviderAutoCompleteTask(ProviderTask):

    def do_run(self):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
        for resp in helpers.streaming_bulk(es_client, self.bulk_stream()):
            logger.debug(resp)

    def bulk_stream(self):
        ShareUser = apps.get_model('share.ShareUser')
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': 'autocomplete'}
        for provider in ShareUser.objects.exclude(robot='').exclude(long_title='').all():
            yield {'_op_type': 'index', '_id': provider.robot, **self.serialize(provider), **opts}

    def serialize(self, provider):
        return {
            '@id': str(provider.pk),
            '@type': 'provider',
            'text': provider.long_title,
        }
