import re

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.oai import OAICreativeWork, OAIPerson, OAINormalizer, Parser


class Person(OAIPerson):
    suffix = ParseName(ctx[0]).suffix
    family_name = ParseName(ctx[0]).last
    given_name = ParseName(ctx[0]).first
    additional_name = ParseName(ctx[0]).middle

    class Extra:
        identifiers = ctx[1]


class Contributor(Parser):
    person = Delegate(Person, ctx)

    class Extra:
        type = 'Contributor'


class Creator(Parser):
    schema = 'Contributor'
    person = Delegate(Person, ctx)

    class Extra:
        type = 'Creator'


class LSHTMCreativeWork(OAICreativeWork):
    contributors = Concat(
        Map(
            Delegate(Creator),
            RunPython(
                'get_contributor_list',
                ctx.record.metadata.dc,
                'creator'
            )
        ),
        Map(
            Delegate(Contributor),
            RunPython(
                'get_contributor_list',
                ctx.record.metadata.dc,
                'contributor'
            )
        )
    )

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
