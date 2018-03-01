from share.regulate.steps import NodeStep
from share.transform.chain.links import IRILink
from share.transform.chain.exceptions import InvalidIRI


class NormalizeIRIs(NodeStep):
    def __init__(self, *args,
                 iri_field='uri',
                 scheme_field='scheme',
                 authority_field='host',
                 blocked_schemes=None,
                 blocked_authorities=None,
                 **kwargs):
        super().__init__(*args, **kwargs)

        self.iri_field = iri_field
        self.scheme_field = scheme_field
        self.authority_field = authority_field
        self.blocked_schemes = blocked_schemes
        self.blocked_authorities = blocked_authorities

    def regulate_node(self, node):
        old_iri = node[self.iri_field]
        try:
            ret = IRILink().execute(old_iri)
            node[self.authority_field] = ret['authority']
            node[self.scheme_field] = ret['scheme']

            new_iri = ret['IRI']
            if old_iri != new_iri:
                node[self.iri_field] = new_iri
                self.info('Normalized IRI "{}" into "{}"'.format(old_iri, new_iri), node.id)

            if self.blocked_schemes and ret['scheme'] in self.blocked_schemes:
                node.delete()
                self.info('Discarding identifier based on invalid scheme "{}"'.format(ret['scheme']), node.id)
            elif self.blocked_authorities and ret['authority'] in self.blocked_authorities:
                node.delete()
                self.info('Discarding identifier based on invalid authority "{}"'.format(ret['authority']), node.id)

        except InvalidIRI as e:
            node.delete()
            self.info('Discarding identifier based on unrecognized IRI "{}"'.format(old_iri))
