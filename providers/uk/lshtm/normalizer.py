import re

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.oai import OAICreativeWork, OAIPerson, OAINormalizer, Parser, OAIPublisher


class PersonIdentifier(Parser):
    url = IRI(ctx)


class WorkIdentifier(Parser):
    url = Try(DOI(ctx[0]))


class Person(OAIPerson):
    suffix = ParseName(ctx[0]).suffix
    family_name = ParseName(ctx[0]).last
    given_name = ParseName(ctx[0]).first
    additional_name = ParseName(ctx[0]).middle

    # see http://researchonline.lshtm.ac.uk/view/creators/105347.html
    identifiers = Map(Delegate(PersonIdentifier), ctx[1])


class Contributor(Parser):
    entity = Delegate(Person, ctx)
    order_cited = ctx('index')

    class Extra:
        type = 'Contributor'


class Creator(Parser):
    schema = 'Contributor'
    entity = Delegate(Person, ctx)
    order_cited = ctx('index')

    class Extra:
        type = 'Creator'


class LSHTMCreativeWork(OAICreativeWork):

    def get_schema(self, types):
        schemes = {
            'Conference or Workshop Item': 'ConferencePaper',
            'Article': 'Article'
        }
        for listing in types:
            if listing == 'PeerReviewd' or listing == 'NotPeerReviewed':
                continue
            return schemes.get(listing) or 'CreativeWork'

    schema = RunPython('get_schema', Concat(ctx.record.metadata.dc['dc:type']))

    related_entities = Concat(
        Map(Delegate(Contributor), RunPython(
            'get_contributor_list',
            ctx.record.metadata.dc,
            'contributor'
        )),
        Map(Delegate(Creator), RunPython(
            'get_contributor_list',
            ctx.record.metadata.dc,
            'creator'
        )),
        Map(Delegate(OAIPublisher), ctx.publisher),
    )

    identifier = Delegate(WorkIdentifier, Concat(ctx.record.metadata.dc['dc:relation']))

    def get_contributor_list(self, ctx, type):
        """
        Create list of tuples  of all contributors/creators in the form (Contributor, URL) where URL may be None
        """
        if 'dc:' + type not in ctx:
            return []
        if 'dc:identifier' not in ctx:
            return []

        people = {x: None for x in ctx['dc:' + type]}

        for identifier in Concat(ctx['dc:identifier']):
            for ele in identifier.split(';'):
                url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                                 ele)
                if url:
                    url = url[0].rstrip('>')
                    name = ele.split(' <')[0]
                    people[name] = url
        return list(people.items())


class LSHTMNormalizer(OAINormalizer):
    root_parser = LSHTMCreativeWork
