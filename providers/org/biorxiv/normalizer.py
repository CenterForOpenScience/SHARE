from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class DoiLink(Parser):
    schema = 'Link'

    url = tools.RunPython(format_doi_as_url, ctx)
    type = tools.Static('doi')


class DoiThroughLinks(Parser):
    schema = 'ThroughLinks'

    link = tools.Delegate(DoiLink, ctx)


class Link(Parser):
    url = ctx
    type = tools.RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'biorxiv.org' in link:
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


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


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

    links = tools.Concat(
        tools.Map(
            tools.Delegate(ThroughLinks),
            tools.Concat(
                ctx['og:url'],
                ctx['citation_public_url']
            )
        ),
        tools.Map(
            tools.Delegate(DoiThroughLinks),
            tools.Concat(
                ctx['citation_doi']
            )
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

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Concat(
            tools.Try(ctx['category'])
        )
    )

    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Concat(tools.Static('Biology and life sciences'))
    )

    class Extra:
        identifiers = ctx['DC.Identifier']
        access_rights = ctx['DC.AccessRights']
        record_type = ctx['type']
        citation_author = ctx['citation_author']
        citation_author_institution = ctx['citation_author_institution']
        citation_author_email = ctx['citation_author_email']
