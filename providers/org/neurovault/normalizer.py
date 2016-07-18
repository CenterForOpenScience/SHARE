import re

from share.normalize import *
from share.normalize.utils import format_doi_as_url


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx
    person = Delegate(Person, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        elif 'neurovault.org' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = Maybe(ctx, 'name')
    description = Maybe(ctx, 'description')
    date_updated = ParseDate(Maybe(ctx, 'modify_date'))
    contributors = Map(Delegate(Contributor), RunPython('parse_names', Maybe(ctx, 'authors')))
    links = Map(Delegate(ThroughLinks), Concat(
        Maybe(ctx, 'url'),
        Maybe(ctx, 'full_dataset_url'),
        RunPython('format_doi_url', Maybe(ctx, 'DOI')),
        Maybe(ctx, 'paper_url')
    ))

    def parse_names(self, authors):
        return re.split(',\s|\sand\s', authors)

    def format_doi_url(self, doi):
        if doi:
            return format_doi_as_url(self, doi)
        return None
