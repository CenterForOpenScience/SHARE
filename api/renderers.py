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

    # override from JSONAPIRenderer to include conflicted data in 409 responses
    def render_errors(self, data, accepted_media_type=None, renderer_context=None):
        conflicting_data = renderer_context.pop('conflicting_data', None)
        if True: #conflicting_data is None:
            return super().render_errors(data, accepted_media_type, renderer_context)

        # render the conflicting data as if there was no error, then add the errors
        response = renderer_context['view'].response
        renderer_context['view'].response = None
        import ipdb; ipdb.set_trace()
        rendered_data = super().render(conflicting_data, accepted_media_type, renderer_context)

        # use the grandparent render()
        return super(JSONAPIRenderer, self).render({
            'data': rendered_data,
            'errors': data
        }, accepted_media_type, renderer_context)


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
