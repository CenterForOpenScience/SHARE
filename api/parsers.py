import six
import ujson
import jsonschema

from django.conf import settings
from rest_framework import renderers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser

from api import schemas


class JSONLDParser(JSONParser):
    """
    Parses JSON-serialized data.
    """
    media_type = 'application/json'
    renderer_class = renderers.JSONRenderer

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            data = stream.read().decode(encoding)
            return ujson.loads(data)  # UJSON ftw.
        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % six.text_type(exc))


class V1SchemaParser(JSONParser):
    """
    Validates JSON data using the SHARE v1 schema.
    """
    def parse(self, stream, media_type=None, parser_context=None):
        data = super(V1SchemaParser, self).parse(stream, media_type, parser_context)
        try:
            jsonschema.validate(data, schemas.v1_push_schema)
        except ValueError as error:
            raise ParseError(detail=error.message)
        else:
            return data
