from share.legacy_normalize.regulate.steps import NodeStep
from share.legacy_normalize.transform.chain.links import IRILink
from share.legacy_normalize.transform.chain.exceptions import InvalidIRI


class NormalizeIRIs(NodeStep):
    """Normalize identifiers into consistent IRI formats.

    Parse out the IRI's scheme and authority and set them on the identifier model.

    Settings:
        [urn_fallback]: Boolean (default False). If True, unrecognized identifiers will
            be normalized into a URN with authority "share", e.g. `urn://share/123`.
            If False, nodes with unrecognized identifiers will be discarded.
        [blocked_schemes]: Optional list of schemes. Identifier nodes with a blocked
            scheme will be discarded.
        [blocked_authorities]: Optional list of authorities. Identifier nodes with
            a blocked authority will be discarded.
        [iri_field]: Field in which the IRI is stored (default 'uri')
        [scheme_field]: Field in which the IRI's scheme is stored (default 'scheme')
        [authority_field]: Field in which the IRI's authority is stored (default 'host')
        [node_types]: Optional list of node types (inherited from NodeStep).
            If given, filter the list of nodes this step will consider.

    Example config:
        Normalize work identifier IRIs. Discard work identifiers with scheme 'mailto', or
        with authority 'issn' or 'orcid.org'.

        ```json
        {
            'namespace': 'share.regulate.steps.node',
            'name': 'normalize_iris',
            'settings': {
                'node_types': ['workidentifier'],
                'blocked_schemes': ['mailto'],
                'blocked_authorities': ['issn', 'orcid.org'],
            },
        },
        ```
    """
    def __init__(self, *args,
                 blocked_schemes=None,
                 blocked_authorities=None,
                 urn_fallback=False,
                 iri_field='uri',
                 scheme_field='scheme',
                 authority_field='host',
                 **kwargs):
        super().__init__(*args, **kwargs)

        self.iri_field = iri_field
        self.scheme_field = scheme_field
        self.authority_field = authority_field
        self.blocked_schemes = blocked_schemes
        self.blocked_authorities = blocked_authorities
        self.urn_fallback = urn_fallback

    def regulate_node(self, node):
        old_iri = node[self.iri_field]
        try:
            ret = IRILink(urn_fallback=self.urn_fallback).execute(old_iri)
            node[self.authority_field] = ret['authority']
            node[self.scheme_field] = ret['scheme']

            new_iri = ret['IRI']
            if old_iri != new_iri:
                node[self.iri_field] = new_iri
                self.info('Normalized IRI "{}" into "{}"'.format(old_iri, new_iri), node.id)

            if self.blocked_schemes and ret['scheme'] in self.blocked_schemes:
                self.info('Discarding identifier based on invalid scheme "{}"'.format(ret['scheme']), node.id)
                node.delete()
            elif self.blocked_authorities and ret['authority'] in self.blocked_authorities:
                self.info('Discarding identifier based on invalid authority "{}"'.format(ret['authority']), node.id)
                node.delete()

        except InvalidIRI:
            self.info('Discarding identifier based on unrecognized IRI "{}"'.format(old_iri), node.id)
            node.delete()
