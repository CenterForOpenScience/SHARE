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

from bots.elasticsearch import util

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


class IndexModelTask(ProviderTask):

    def do_run(self, model_name, ids):
        errors = []
        model = apps.get_model('share', model_name)
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=30)

        for ok, resp in helpers.streaming_bulk(es_client, self.bulk_stream(model, ids), raise_on_error=False):
            if not ok:
                logger.warning(resp)
            else:
                logger.debug(resp)

            if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                errors.append(resp)

        if errors:
            raise Exception('Failed to index documents {}'.format(errors))

    def bulk_stream(self, model, ids):
        if not ids:
            return

        opts = {'_index': settings.ELASTICSEARCH_INDEX, '_type': model.__name__.lower()}

        if model is AbstractCreativeWork:
            for blob in util.fetch_abstractcreativework(ids):
                if blob['is_deleted']:
                    yield {'_id': blob['id'], '_op_type': 'delete', **opts}
                else:
                    yield {'_id': blob['id'], '_op_type': 'index', **blob, **opts}
            return

        if model is Person:
            for blob in util.fetch_person(ids):
                yield {'_id': blob['id'], '_op_type': 'index', **blob, **opts}
            return

        for inst in model.objects.filter(id__in=ids):
            # if inst.is_delete:  # TODO
            #     yield {'_id': inst.pk, '_op_type': 'delete', **opts}
            yield {'_id': inst.pk, '_op_type': 'index', **self.serialize(inst), **opts}

    def serialize(self, inst):
        return {
            Entity: self.serialize_entity,
            Person: self.serialize_person,
            Tag: self.serialize_tag,
            Subject: self.serialize_subject,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_person(self, person, suggest=True):
        serialized_person = util.fetch_person(person.pk)
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


class IndexSourceTask(ProviderTask):

    def do_run(self):
        es_client = Elasticsearch(settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=30)
        errors = []
        for ok, resp in helpers.streaming_bulk(es_client, self.bulk_stream(), raise_on_error=False):
            if not ok:
                logger.warning(resp)
            else:
                logger.debug(resp)

            if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                errors.append(resp)

        if errors:
            raise Exception('Failed to index documents {}'.format(errors))

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
