import abc
import json
import uuid
import re
from collections import OrderedDict

import xmltodict

from share.transform.tools.links import Context, IRILink


# NOTE: Context is a thread local singleton
# It is assigned to ctx here just to keep a family interface
ctx = Context()


class TransformerMeta(type):
    def __init__(cls, name, bases, attrs):
        if hasattr(cls, 'registry'):
            assert 'KEY' in attrs and attrs['KEY'] not in cls.registry
            cls.registry[attrs['KEY']] = cls
        else:
            # base class
            cls.registry = {}


class Transformer(metaclass=abc.ABCMeta):

    root_parser = None

    NAMESPACES = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
    }

    EMPTY_RE = re.compile(r'\s*(|none|empty)\s*', flags=re.I)

    def __init__(self, app_config):
        self.config = app_config
        self.namespaces = getattr(self.config, 'namespaces', self.NAMESPACES)

    @property
    def allowed_roots(self):
        from share.models import AbstractCreativeWork
        return set(t.__name__ for t in AbstractCreativeWork.get_type_classes())

    def do_normalize(self, data):
        parsed = self.unwrap_data(data)
        self.remove_empty_values(parsed)
        parser = self.get_root_parser()

        return parser(parsed).parse()

    def unwrap_data(self, data):
        if data.startswith('<'):
            return xmltodict.parse(data, process_namespaces=True, namespaces=self.namespaces)
        else:
            return json.loads(data, object_pairs_hook=OrderedDict)

    def get_root_parser(self):
        if self.root_parser:
            return self.root_parser

        try:
            module = __import__(self.config.name + '.normalizer', fromlist=('Manuscript', ))
        except ImportError:
            raise ImportError('Unable to find parser definitions at {}'.format(self.config.name + '.normalizer'))

        root_levels = [
            getattr(module, class_name)
            for class_name in self.allowed_roots
            if hasattr(module, class_name)
        ]

        root_levels = [parser for parser in root_levels if getattr(parser, 'is_root', False)] or root_levels

        if not root_levels:
            raise ImportError('No root level parsers found. You may have to create one or manually specifiy a parser with the root_parser attribute')

        if len(root_levels) > 1:
            raise ImportError('Found root level parsers {!r}. If more than one is found a single parser must be specified via the root_parser attribute'.format(root_levels))

        return root_levels[0]

    def normalize(self, raw_data):
        ctx.clear()  # Just incase
        ctx._config = self.config
        source_id = None
        # Parsed data will be loaded into ctx
        if not isinstance(raw_data, (str, bytes)):
            source_id = raw_data.provider_doc_id
            raw_data = raw_data.data
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode()
        root_ref = self.do_normalize(raw_data)
        jsonld = ctx.jsonld

        if source_id and jsonld and root_ref:
            self.add_source_identifier(source_id, jsonld, root_ref)

        ctx.clear()  # Clean up

        return jsonld

    def add_source_identifier(self, source_id, jsonld, root_ref):
        uri = IRILink(urn_fallback=True).execute(str(source_id))['IRI']
        if any(n['@type'].lower() == 'workidentifier' and n['uri'] == uri for n in jsonld['@graph']):
            return

        identifier_ref = {
            '@id': '_:' + uuid.uuid4().hex,
            '@type': 'workidentifier'
        }
        identifier = {
            'uri': uri,
            'creative_work': root_ref,
            **identifier_ref
        }
        ctx.pool[root_ref].setdefault('identifiers', []).append(identifier_ref)
        jsonld['@graph'].append(identifier)

    def remove_empty_values(self, parsed):
        if isinstance(parsed, dict):
            ret = OrderedDict()
            for k, v in parsed.items():
                if isinstance(v, (dict, list)):
                    v = self.remove_empty_values(v)
                if isinstance(v, str) and self.EMPTY_RE.fullmatch(v):
                    continue
                ret[k] = v
            return ret

        ret = []
        for v in parsed:
            if isinstance(v, (dict, list)):
                v = self.remove_empty_values(v)
            if isinstance(v, str) and self.EMPTY_RE.fullmatch(v):
                continue
            ret.append(v)
        return ret


#         if isinstance(parsed, dict):
#             items = parsed.items()
#         elif isinstance(parsed, list):
#             items = zip(range(len(parsed)), parsed)
#         else:
#             raise TypeError('parsed must be a dict or list')

#         for k, v in tuple(items):
#             if isinstance(v, (dict, list)):
#                 self.remove_empty_values(v)
#             elif self.EMPTY_RE.fullmatch(str(v)):
#                 parsed.pop(k)
