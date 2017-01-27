import logging
import re

from django.apps import apps
from django.conf import settings

from elasticsearch import helpers
from elasticsearch import Elasticsearch

from share.models import Agent
from share.models import CreativeWork
from share.models import Subject
from share.models import Tag
from share.tasks import AppTask
from share.util import IDObfuscator

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


class IndexModelTask(AppTask):

    def do_run(self, model_name, ids, es_url=None, es_index=None):
        errors = []
        model = apps.get_model('share', model_name)
        es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)

        for ok, resp in helpers.streaming_bulk(es_client, self.bulk_stream(model, ids, es_index or settings.ELASTICSEARCH_INDEX), raise_on_error=False):
            if not ok:
                logger.warning(resp)
            else:
                logger.debug(resp)

            if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                errors.append(resp)

        if errors:
            raise Exception('Failed to index documents {}'.format(errors))

    def bulk_stream(self, model, ids, es_index):
        if not ids:
            return

        opts = {'_index': es_index, '_type': model._meta.verbose_name_plural.replace(' ', '')}

        if model is CreativeWork:
            for blob in util.fetch_creativework(ids):
                if blob.pop('is_deleted') or blob.pop('same_as'):
                    yield {'_id': blob['id'], '_op_type': 'delete', **opts}
                else:
                    yield {'_id': blob['id'], '_op_type': 'index', **blob, **opts}
            return

        if model is Agent:
            for blob in util.fetch_agent(ids):
                if blob.pop('same_as'):
                    yield {'_id': blob['id'], '_op_type': 'delete', **opts}
                else:
                    yield {'_id': blob['id'], '_op_type': 'index', **blob, **opts}
            return

        for inst in model.objects.filter(id__in=ids):
            # if inst.is_delete:  # TODO
            #     yield {'_id': inst.pk, '_op_type': 'delete', **opts}
            yield {'_id': inst.pk, '_op_type': 'index', **self.serialize(inst), **opts}

    def serialize(self, inst):
        return {
            Tag: self.serialize_tag,
            Subject: self.serialize_subject,
        }[type(inst)._meta.concrete_model](inst)

    def serialize_tag(self, tag):
        return {
            'id': IDObfuscator.encode(tag),
            'type': 'tag',
            'name': safe_substr(tag.name),
        }

    def serialize_subject(self, subject):
        return {
            'id': IDObfuscator.encode(subject),
            'type': 'subject',
            'name': safe_substr(subject.name),
        }


class IndexSourceTask(AppTask):

    def do_run(self, es_url=None, es_index=None):
        es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)
        errors = []
        for ok, resp in helpers.streaming_bulk(es_client, self.bulk_stream(es_index or settings.ELASTICSEARCH_INDEX), raise_on_error=False):
            if not ok:
                logger.warning(resp)
            else:
                logger.debug(resp)

            if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                errors.append(resp)

        if errors:
            raise Exception('Failed to index documents {}'.format(errors))

    def bulk_stream(self, es_index):
        ShareUser = apps.get_model('share.ShareUser')
        opts = {'_index': es_index, '_type': 'sources'}
        for source in ShareUser.objects.exclude(robot='').exclude(long_title='').all():
            yield {'_op_type': 'index', '_id': source.robot, **self.serialize(source), **opts}

    def serialize(self, source):
        return {
            'id': source.robot,
            'type': 'source',
            'name': safe_substr(source.long_title),
            'short_name': safe_substr(source.robot)
        }
