import arrow

import dateparser

from share.normalize import Parser, Static, Delegate, RunPython, ParseName, Normalizer, Maybe, Concat, Map, ctx, Try
from share.normalize.utils import format_doi_as_url


class ISSN(Parser):
    schema = 'Link'
    url = ctx
    type = Static('issn')


class Email(Parser):
    email = ctx


class PersonEmail(Parser):
    email = Delegate(Email, ctx)


class Institution:
    name = ctx.author_institution


class Affiliation:
    # The entity used here could be any of the entity subclasses (Institution, Publisher, Funder, Organization).
    entity = Delegate(Institution, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'peerj.com' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = (Delegate(Tag), ctx)


class Publisher(Parser):
    name = ctx


class Institution(Parser):
    name = RunPython('get_author_institute', ctx)

    def get_author_institute(self, context):
        # read into a set while preserving order and passed back to erase duplicates
        seen = set()
        if 'author_institution' in context:
            if isinstance(context['author_institution'], str):
                return [x for x in [context['author_institution']] if x not in seen and not seen.add(x)]
            return [x for x in context['author_institution'] if x not in seen and not seen.add(x)]
        return [x for x in context['author_institutions'].split('; ') if x not in seen and not seen.add(x)]


class Institutions(Parser):
    name = ctx


class Association(Parser):
    pass


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class CreativeWork(Parser):
    title = ctx.title
    description = Maybe(ctx, 'description-html')
    contributors = Map(Delegate(Contributor), ctx.author)
    links = Concat(
        Map(Delegate(ThroughLinks), ctx.pdf_url),
        Map(Delegate(ThroughLinks), RunPython('format_doi', ctx.doi)),
        Delegate(ThroughLinks.using(link=Delegate(ISSN)), Maybe(ctx, 'issn')),
        Map(Delegate(ThroughLinks), ctx.fulltext_html_url)
    )
    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.publisher
    )
    institutions = Map(
        Delegate(Association.using(entity=Delegate(Institution))),
        ctx
    )
    subject = Delegate(Tag, ctx.subjects[0])
    date_created = RunPython('parse_date', ctx.date)
    date_published = RunPython('parse_date', ctx.date)
    language = ctx.language
    tags = Concat(
        Delegate(Tag, ctx.subjects),
        Map(Delegate(ThroughTags), Maybe(ctx, 'keywords'))
    )

    class Extra:
        modified = RunPython('parse_date', ctx.date)
        subjects = Maybe(ctx, 'subjects')
        affiliations = Map(
            Delegate(Association.using(entity=Delegate(Institution))),
            ctx
        )
        identifiers = ctx.identifiers
        volume = Try(ctx.volume)
        emails = Maybe(ctx, 'author_email')
        journal_title = Try(ctx.journal_title)
        journal_abbrev = Try(ctx.journal_abbrev)
        description_nohtml = ctx.description

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()


class Preprint(CreativeWork):

    class Extra:
        modified = RunPython('parse_date', ctx.date)
        subjects = Maybe(ctx, 'subjects')
        affiliations = Map(
            Delegate(Association.using(entity=Delegate(Institution))),
            ctx
        )
        identifiers = ctx.identifiers
        emails = Maybe(ctx, 'author_email')
        description_nohtml = ctx.description


class PeerJNormalizer(Normalizer):

    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)
        if 'preprint' in unwrapped['_links']['self']['href']:
            return Preprint(unwrapped).parse()
        return CreativeWork(unwrapped).parse()
