import ujson
import six
from collections import OrderedDict

from django.utils import encoding

# from rest_framework.compat import SHORT_SEPARATORS, LONG_SEPARATORS, INDENT_SEPARATORS
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.utils import encoders
from rest_framework import relations
from rest_framework.serializers import BaseSerializer

from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
from rest_framework_json_api import utils


class HideNullJSONAPIRenderer(JSONAPIRenderer):

    @staticmethod
    def extract_attributes(fields, resource):
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

    @classmethod
    def build_json_resource_obj(cls, fields, resource, resource_instance, resource_name):
        resource_data = [
            ('type', resource_name),
            ('id', encoding.force_text(resource_instance.pk) if resource_instance else None),
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
