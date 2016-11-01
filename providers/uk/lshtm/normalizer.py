import re

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.oai import OAICreativeWork, OAINormalizer, Parser, OAIPublisher


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = RunPython('get_identifier', ctx)

    def get_identifier(self, ctx):
        if re.findall('^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$', ctx):
            return ctx


class Person(Parser):
    suffix = ParseName(ctx[0]).suffix
    family_name = ParseName(ctx[0]).last
    given_name = ParseName(ctx[0]).first
    additional_name = ParseName(ctx[0]).middle

    # see http://researchonline.lshtm.ac.uk/view/creators/105347.html
    identifiers = Map(Delegate(AgentIdentifier), ctx[1])


class Contributor(Parser):
    agent = Delegate(Person, ctx)

    class Extra:
        type = 'Contributor'


class Creator(Parser):
    schema = 'Contributor'
    agent = Delegate(Person, ctx)

    class Extra:
        type = 'Creator'


class LSHTMCreativeWork(OAICreativeWork):

    def get_schema(self, types):
        schemes = {
            'Conference or Workshop Item': 'ConferencePaper',
            'Article': 'Article'
        }
        for listing in types:
            if listing == 'PeerReviewed' or listing == 'NotPeerReviewed':
                continue
            return schemes.get(listing) or 'CreativeWork'

    schema = RunPython('get_schema', Concat(ctx.record.metadata.dc['dc:type']))

    related_agents = Concat(
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
        Map(Delegate(OAIPublisher), Try(ctx.record.metadata.dc['dc:publisher'])),
    )

    identifiers = Map(Delegate(WorkIdentifier), Concat(
        Try(ctx.record.metadata.dc['dc:relation']),
        Try(ctx.record.metadata.dc['dc:identifier'])))

    def get_contributor_list(self, ctx, type):
        """
        Create list of tuples  of all contributors/creators in the form (Contributor, URL) where URL may be None
        """
        # No creators/contributors
        if 'dc:' + type not in ctx:
            return []

        people = {x: None for x in ctx['dc:' + type]}

        # No identifiers
        if 'dc:identifier' not in ctx:
            return list(people.items())

        for identifier in ctx['dc:identifier']:
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
