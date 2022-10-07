import re

from share.legacy_normalize.transform.chain import *


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Creator(Parser):
    order_cited = ctx('index')
    cited_as = ctx
    agent = Delegate(Person, ctx)


class CreativeWork(Parser):
    title = Try(ctx.name)
    description = Try(ctx.description)
    date_published = ParseDate(Try(ctx.add_date))
    date_updated = ParseDate(Try(ctx.modify_date))

    related_agents = Map(Delegate(Creator), RunPython('parse_names', Try(ctx.authors)))

    identifiers = Map(
        Delegate(WorkIdentifier),
        Try(ctx.DOI),
        Try(ctx.full_dataset_url),
        Try(ctx.paper_url),
        Try(ctx.url),
    )

    def parse_names(self, authors):
        if not authors:
            return []
        return re.split(r',\s|\sand\s', authors)


class NeurovaultTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
