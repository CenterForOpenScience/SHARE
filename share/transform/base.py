import abc
import json
import uuid
import re
from collections import OrderedDict

import xmltodict


class TransformerMeta(type):
    def __init__(cls, name, bases, attrs):
        if hasattr(cls, 'registry'):
            if 'KEY' in attrs:
                assert 'VERSION' in attrs, 'Registered transformers must have a version'
                assert attrs['KEY'] not in cls.registry, 'Transformer keys must be unique'
                cls.registry[attrs['KEY']] = cls
        else:
            # base class
            cls.registry = {}


class BaseTransformer(metaclass=TransformerMeta):

    NAMESPACES = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
    }

    EMPTY_RE = re.compile(r'\s*(|none|empty)\s*', flags=re.I)

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.namespaces = kwargs.get('namespaces', self.NAMESPACES)

    def do_transform(self, data):
        raise NotImplementedError('Transformers must implement do_transform')

    def transform(self, raw_data):
        source_id = None
        if not isinstance(raw_data, (str, bytes)):
            source_id = raw_data.suid.identifier
            raw_data = raw_data.data
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode()
        jsonld, root_ref = self.do_transform(raw_data)

        if source_id and jsonld and root_ref:
            self.add_source_identifier(source_id, jsonld, root_ref)

        return jsonld

    def add_source_identifier(self, source_id, jsonld, root_ref):
        from share.transform.chain.links import IRILink
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
        root_node = next(n for n in jsonld['@graph'] if n['@id'] == root_ref['@id'] and n['@type'] == root_ref['@type'])
        root_node.setdefault('identifiers', []).append(identifier_ref)
        jsonld['@graph'].append(identifier)

