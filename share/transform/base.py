import abc
import uuid

from share.regulate.graph import MutableGraph


class BaseTransformer(metaclass=abc.ABCMeta):

    def __init__(self, source_config, **kwargs):
        self.config = source_config
        self.kwargs = kwargs

    @abc.abstractmethod
    def do_transform(self, datum):
        raise NotImplementedError('Transformers must implement do_transform')

    def transform(self, datum):
        source_id = None
        if not isinstance(datum, (str, bytes)):
            source_id = datum.suid.identifier
            datum = datum.datum
        if isinstance(datum, bytes):
            datum = datum.decode()
        jsonld, root_ref = self.do_transform(datum)

        if source_id and jsonld and root_ref:
            self.add_source_identifier(source_id, jsonld, root_ref)

        # TODO return a MutableGraph from do_transform, maybe build it directly in Parser?
        return MutableGraph.from_jsonld(jsonld)

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
