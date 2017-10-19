import ujson
import six
from collections import OrderedDict

from django.utils import encoding
from django.apps import apps

# from rest_framework.compat import SHORT_SEPARATORS, LONG_SEPARATORS, INDENT_SEPARATORS
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.utils import encoders
from rest_framework import relations
from rest_framework.serializers import BaseSerializer, Serializer, ListSerializer

from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
from rest_framework_json_api import utils

from share.util import IDObfuscator


class HideNullJSONAPIRenderer(JSONAPIRenderer):

    # override null behavior from JSONAPIRenderer
    @classmethod
    def extract_attributes(cls, fields, resource):
        data = OrderedDict()
        for field_name, field in six.iteritems(fields):
            # ID is always provided in the root of JSON API so remove it from attributes
            if field_name == 'id':
                continue
            # don't output a key for write only fields
            if fields[field_name].write_only:
                continue
            # Skip fields with relations
            if isinstance(field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)):
                continue

            # Skip read_only attribute fields when `resource` is an empty
            # serializer. Prevents the "Raw Data" form of the browsable API
            # from rendering `"foo": null` for read only fields
            try:
                resource[field_name]
            except KeyError:
                if fields[field_name].read_only or fields[field_name].allow_null:
                    continue

            data.update({
                field_name: resource.get(field_name)
            })

        return utils.format_keys(data)

    def encode_id(resource_id, resource_type):
        return encoding.force_text(IDObfuscator.encode_id(resource_id, apps.get_model('share', resource_type)))

    @classmethod
    def encode_ids(cls, relation_data):
        if relation_data:
            if isinstance(relation_data, list):
                for obj in relation_data:
                    obj['id'] = cls.encode_id(int(obj['id']), obj['type'])
            else:
                relation_data['id'] = cls.encode_id(int(relation_data['id']), relation_data['type'])
        return relation_data

    # override ids in relationships from JSONAPIRenderer
    @classmethod
    def extract_relationships(cls, fields, resource, resource_instance):
        # Avoid circular deps
        from rest_framework_json_api.relations import ResourceRelatedField

        data = OrderedDict()

        # Don't try to extract relationships from a non-existent resource
        if resource_instance is None:
            return

        for field_name, field in six.iteritems(fields):
            # Skip URL field
            if field_name == api_settings.URL_FIELD_NAME:
                continue

            # Skip fields without relations
            if not isinstance(field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)):
                continue

            source = field.source
            relation_type = utils.get_related_resource_type(field)

            if isinstance(field, relations.HyperlinkedIdentityField):
                resolved, relation_instance = utils.get_relation_instance(resource_instance, source, field.parent)
                if not resolved:
                    continue
                # special case for HyperlinkedIdentityField
                relation_data = list()

                # Don't try to query an empty relation
                relation_queryset = relation_instance \
                    if relation_instance is not None else list()

                for related_object in relation_queryset:
                    relation_data.append(
                        OrderedDict([('type', relation_type), ('id', encoding.force_text(related_object.pk))])
                    )

                data.update({field_name: {
                    'links': {
                        'related': resource.get(field_name)
                    },
                    'data': cls.encode_ids(relation_data),
                    'meta': {
                        'count': len(relation_data)
                    }
                }})
                continue

            if isinstance(field, ResourceRelatedField):
                resolved, relation_instance = utils.get_relation_instance(resource_instance, source, field.parent)
                if not resolved:
                    continue

                # special case for ResourceRelatedField
                relation_data = {
                    'data': cls.encode_ids(resource.get(field_name))
                }

                field_links = field.get_links(resource_instance)
                relation_data.update(
                    {'links': field_links}
                    if field_links else dict()
                )
                data.update({field_name: relation_data})
                continue

            if isinstance(field, (relations.PrimaryKeyRelatedField, relations.HyperlinkedRelatedField)):
                resolved, relation = utils.get_relation_instance(resource_instance, '%s_id' % source, field.parent)
                if not resolved:
                    continue
                relation_id = relation if resource.get(field_name) else None
                relation_data = {
                    'data': (
                        OrderedDict([('type', relation_type), ('id', cls.encode_id(relation_id, relation_type))])
                        if relation_id is not None else None)
                }

                relation_data.update(
                    {'links': {'related': resource.get(field_name)}}
                    if isinstance(field, relations.HyperlinkedRelatedField) and resource.get(field_name) else dict()
                )
                data.update({field_name: relation_data})
                continue

            if isinstance(field, relations.ManyRelatedField):
                resolved, relation_instance = utils.get_relation_instance(resource_instance, source, field.parent)
                if not resolved:
                    continue

                if isinstance(field.child_relation, ResourceRelatedField):
                    # special case for ResourceRelatedField
                    relation_data = {
                        'data': cls.encode_ids(resource.get(field_name))
                    }

                    field_links = field.child_relation.get_links(resource_instance)
                    relation_data.update(
                        {'links': field_links}
                        if field_links else dict()
                    )
                    relation_data.update(
                        {
                            'meta': {
                                'count': len(resource.get(field_name))
                            }
                        }
                    )
                    data.update({field_name: relation_data})
                    continue

                relation_data = list()
                for nested_resource_instance in relation_instance:
                    nested_resource_instance_type = (
                        relation_type or
                        utils.get_resource_type_from_instance(nested_resource_instance)
                    )

                    relation_data.append(OrderedDict([
                        ('type', nested_resource_instance_type),
                        ('id', encoding.force_text(nested_resource_instance.pk))
                    ]))
                data.update({
                    field_name: {
                        'data': cls.encode_ids(relation_data),
                        'meta': {
                            'count': len(relation_data)
                        }
                    }
                })
                continue

            if isinstance(field, ListSerializer):
                resolved, relation_instance = utils.get_relation_instance(resource_instance, source, field.parent)
                if not resolved:
                    continue

                relation_data = list()

                serializer_data = resource.get(field_name)
                resource_instance_queryset = list(relation_instance)
                if isinstance(serializer_data, list):
                    for position in range(len(serializer_data)):
                        nested_resource_instance = resource_instance_queryset[position]
                        nested_resource_instance_type = (
                            relation_type or
                            utils.get_resource_type_from_instance(nested_resource_instance)
                        )

                        relation_data.append(OrderedDict([
                            ('type', nested_resource_instance_type),
                            ('id', encoding.force_text(nested_resource_instance.pk))
                        ]))

                    data.update({field_name: {'data': cls.encode_ids(relation_data)}})
                    continue

            if isinstance(field, Serializer):
                resolved, relation_instance = utils.get_relation_instance(resource_instance, source, field.parent)
                if not resolved:
                    continue

                data.update({
                    field_name: {
                        'data': (
                            OrderedDict([
                                ('type', relation_type),
                                ('id', cls.encode_id(resource_instance.pk, relation_type))
                            ]) if resource.get(field_name) else None)
                    }
                })
                continue

        return utils.format_keys(data)

    # override top level id from JSONAPIRenderer
    @classmethod
    def build_json_resource_obj(cls, fields, resource, resource_instance, resource_name):
        resource_data = [
            ('type', resource_name),
            ('id', cls.encode_id(resource_instance.pk, resource_instance._meta.model.__name__) if resource_instance and resource_instance.pk else None),
            ('attributes', cls.extract_attributes(fields, resource)),
        ]
        relationships = cls.extract_relationships(fields, resource, resource_instance)
        if relationships:
            resource_data.append(('relationships', relationships))
        # Add 'self' link if field is present and valid
        if api_settings.URL_FIELD_NAME in resource and \
                isinstance(fields[api_settings.URL_FIELD_NAME], relations.RelatedField):
            resource_data.append(('links', {'self': resource[api_settings.URL_FIELD_NAME]}))
        return OrderedDict(resource_data)


class JSONLDRenderer(JSONRenderer):
    """
    Renderer which serializes to JSON.
    """
    media_type = 'application/vnd.api+json'
    format = 'json'
    encoder_class = encoders.JSONEncoder
    ensure_ascii = not api_settings.UNICODE_JSON
    compact = api_settings.COMPACT_JSON

    # We don't set a charset because JSON is a binary encoding,
    # that can be encoded as utf-8, utf-16 or utf-32.
    # See: http://www.ietf.org/rfc/rfc4627.txt
    # Also: http://lucumr.pocoo.org/2013/7/19/application-mimetypes-and-encodings/
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        if data is None:
            return bytes()

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context) or 4

        # if indent is None:
        #     separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        # else:
        #     separators = INDENT_SEPARATORS

        ret = ujson.dumps(  # UJSON is faster
            data,
            # , cls=self.encoder_class,
            escape_forward_slashes=False,
            indent=indent, ensure_ascii=self.ensure_ascii,
            # separators=separators
        )

        # On python 2.x json.dumps() returns bytestrings if ensure_ascii=True,
        # but if ensure_ascii=False, the return type is underspecified,
        # and may (or may not) be unicode.
        # On python 3.x json.dumps() returns unicode strings.
        if isinstance(ret, six.text_type):
            # We always fully escape \u2028 and \u2029 to ensure we output JSON
            # that is a strict javascript subset. If bytes were returned
            # by json.dumps() then we don't have these characters in any case.
            # See: http://timelessrepo.com/json-isnt-a-javascript-subset
            ret = ret.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
            return bytes(ret.encode('utf-8'))
        return ret
