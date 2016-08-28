import logging
import re

from django.apps import apps
from elasticsearch import helpers
from elasticsearch import Elasticsearch

from project import settings

from share.tasks import ProviderTask
from share.models import AbstractCreativeWork
from share.models import Entity
from share.models import Person
from share.models import Tag
from share.models import Subject
from share.models import Association
from share.models import Funder
from share.models import Publisher
from share.models import Institution
from share.models import Organization

logger = logging.getLogger(__name__)


def safe_substr(value, length=32000):
    if value:
        return str(value)[:length]
    return None


def score_text(text):
    return int(
        (len(re.findall('(?!\d)\w', text)) / (1 + len(re.findall('[\W\d]', text))))
        / (len(text) / 100)
    )


def add_suggest(obj):
    if obj['name']:
        obj['suggest'] = {
            'input': re.split('[\\s,]', obj['name']) + [obj['name']],
            'output': obj['name'],
            'payload': {
                'id': obj['id'],
                'name': obj['name'],
                'type': obj['type'],
            },
            'weight': score_text(obj['name'])
        }
    return obj


__shareuser_cache = {}
def sources(qs):
    sus = []
    for through in qs:
        if through.shareuser_id not in __shareuser_cache:
            __shareuser_cache[through.shareuser_id] = through.shareuser
        sus.append(__shareuser_cache[through.shareuser_id])
    return sus


class IndexModelTask(ProviderTask):

    def do_run(self, model_name, ids):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=30)
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
            AbstractCreativeWork: self.serialize_creative_work,
            Entity: self.serialize_entity,
            Person: self.serialize_person,
            Tag: self.serialize_tag,
            Subject: self.serialize_subject,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_person(self, person, suggest=True):
        serialized_person = {
            'id': person.pk,
            'type': 'person',
            'suffix': safe_substr(person.suffix),
            'given_name': safe_substr(person.given_name),
            'family_name': safe_substr(person.family_name),
            'name': safe_substr(person.get_full_name()),
            'additional_name': safe_substr(person.additional_name),
            'identifiers': [{
                'url': identifier.url,
                'base_url': identifier.base_url,
            } for identifier in person.identifiers.all()],
            'affiliations': [
                self.serialize_entity(affiliation, False)
                for affiliation in
                person.affiliations.all()
            ],
            'sources': [safe_substr(source.long_title) for source in sources(person.sources.through.objects.filter(person=person))]
        }
        return add_suggest(serialized_person) if suggest else serialized_person

    def serialize_entity(self, entity, suggest=True):
        serialized_entity = {
            'id': entity.pk,
            'type': type(entity).__name__.lower(),
            'name': safe_substr(entity.name),
            'url': entity.url,
            'location': safe_substr(entity.location),
        }
        return add_suggest(serialized_entity) if suggest else serialized_entity

    def serialize_tag(self, tag, suggest=True):
        serialized_tag = {
            'id': str(tag.pk),
            'type': 'tag',
            'name': safe_substr(tag.name),
        }
        return add_suggest(serialized_tag) if suggest else serialized_tag

    def serialize_subject(self, subject, suggest=True):
        serialized_subject = {
            'id': str(subject.pk),
            'type': 'subject',
            'name': safe_substr(subject.name),
        }
        return add_suggest(serialized_subject) if suggest else serialized_subject

    def serialize_link(self, link):
        return {
            'type': safe_substr(link.type),
            'url': safe_substr(link.url),
        }

    def serialize_contributor(self, contributor):
        return {
            'cited_name': contributor.cited_name,
            'bibliographic': contributor.bibliographic,
            **self.serialize_person(contributor.person),
        }

    def serialize_creative_work(self, creative_work):
        associations = {}
        for association in Association.objects.filter(creative_work=creative_work).select_related('entity'):
            associations.setdefault(type(association.entity), []).append(association.entity)

        serialized_lists = {
            'links': [self.serialize_link(link) for link in creative_work.links.all()],
            'funders': [self.serialize_entity(entity) for entity in associations.get(Funder, [])],
            'publishers': [self.serialize_entity(entity) for entity in associations.get(Publisher, [])],
            'institutions': [self.serialize_entity(entity) for entity in associations.get(Institution, [])],
            'organizations': [self.serialize_entity(entity) for entity in associations.get(Organization, [])],
            'contributors': [self.serialize_contributor(contrib) for contrib in creative_work.contributor_set.select_related('person').order_by('order_cited')],
        }

        return {
            'type': type(creative_work).__name__.lower(),
            'title': safe_substr(creative_work.title),
            'description': safe_substr(creative_work.description),
            'language': safe_substr(creative_work.language),
            'date': (
                creative_work.date_published or creative_work.date_updated or creative_work.date_created
            ).isoformat(),
            'date_created': creative_work.date_created.isoformat(),
            'date_modified': creative_work.date_modified.isoformat(),
            'date_updated': creative_work.date_updated.isoformat() if creative_work.date_updated else None,
            'date_published': creative_work.date_published.isoformat() if creative_work.date_published else None,
            'tags': [safe_substr(tag) for tag in creative_work.tags.all()],
            'subjects': [safe_substr(subject) for subject in creative_work.subjects.all()],
            'awards': [safe_substr(award) for award in creative_work.awards.all()],
            'venues': [safe_substr(venue) for venue in creative_work.venues.all()],
            'sources': [safe_substr(source.long_title) for source in sources(creative_work.sources.through.objects.filter(abstractcreativework=creative_work))],
            'contributors': [c['name'] for c in serialized_lists['contributors']],
            'funders': [c['name'] for c in serialized_lists['funders']],
            'publishers': [c['name'] for c in serialized_lists['publishers']],
            'institutions': [c['name'] for c in serialized_lists['institutions']],
            'organizations': [c['name'] for c in serialized_lists['organizations']],
            'lists': serialized_lists
        }


class IndexSourceTask(ProviderTask):

    def do_run(self):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=30)
        for resp in helpers.streaming_bulk(es_client, self.bulk_stream()):
            logger.debug(resp)

    def bulk_stream(self):
        ShareUser = apps.get_model('share.ShareUser')
        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': 'source'}
        for source in ShareUser.objects.exclude(robot='').exclude(long_title='').all():
            yield {'_op_type': 'index', '_id': source.robot, **self.serialize(source), **opts}

    def serialize(self, source):
        serialized_source = {
            'id': str(source.pk),
            'type': 'source',
            'name': safe_substr(source.long_title),
            'short_name': safe_substr(source.robot)
        }
        return add_suggest(serialized_source)
