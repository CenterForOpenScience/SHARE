from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Link(Parser):
    url = ctx
    type = tools.RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'philica.com' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Person(Parser):
    given_name = tools.ParseName(ctx).first
    family_name = tools.ParseName(ctx).last
    additional_name = tools.ParseName(ctx).middle
    suffix = tools.ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    person = tools.Delegate(Person, ctx)
    cited_name = ctx


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class Preprint(Parser):

    title = tools.Try(ctx['DC.Title'])
    description = tools.Try(ctx['DC.Description'])
    contributors = tools.Map(
        tools.Delegate(Contributor),
        ctx['DC.Contributor']
    )

    links = tools.Map(
        tools.Delegate(ThroughLinks),
        tools.Concat(
            ctx['href'],
            ctx['citation_public_url']
        )
    )

    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        ctx['DC.Publisher']
    )

    date_updated = tools.ParseDate(ctx['DC.Date'])
    date_published = tools.ParseDate(ctx['article:published_time'])

    language = tools.Try(ctx['DC.Language'])
    rights = tools.Try(ctx['DC.Rights'])

    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Concat(tools.Static('Biology and life sciences'))
    )

    class Extra:
        identifiers = ctx['DC.Identifier']
        access_rights = ctx['DC.AccessRights']


class BiorxivNormalizer(Normalizer):

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
