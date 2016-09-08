import arrow

import dateparser

from share.normalize import Parser, Delegate, RunPython, ParseName, Normalizer, Concat, Map, ctx, Try


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'philica.com' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Association(Parser):
    entity = Delegate(Publisher)


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Preprint(Parser):
    title = Try(ctx['DC.title'])
    description = Try(ctx['DC.description'])
    contributors = Map(Delegate(Contributor), ctx['DC.contributor'])
    links = Map(Delegate(ThroughLinks),
            ctx['href'],
            ctx['DC.source']
    )
    publishers = Map(
        Delegate(Association),
        ctx['DC.publisher']
    )
    subject = Delegate(ThroughTags, ctx['DC.subject'])
    date_created = RunPython('parse_date', ctx['DC.created'])
    date_published = RunPython('parse_date', ctx['DC.dateSubmitted'])
    language = ctx['DC.language']
    rights = ctx['DC.rights']

    class Extra:
        abstract = ctx['DC.abstract']
        coverage = ctx['DC.coverage']
        identifiers = ctx['DC.identifier']
        format_type = ctx['DC.identifier']
        type_publication = ctx['DC.type']
        citation = ctx['DC.biliographicCitation']

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()


class PhilicaNormalizer(Normalizer):

    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)
        unwrapped = self.change_context(unwrapped['data'])
        return Preprint(unwrapped).parse()

    def change_context(self, context):
        bucket = {'href': []}
        for blocks in context:
            if 'name' in blocks:
                bucket.update({blocks['name']: blocks['content']})
            elif 'href' in blocks and not blocks['href'] == 'css/stylesheet.css':
                bucket['href'].append(blocks['href'])
        return bucket
