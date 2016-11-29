from share.normalize import *


class WorkIdentifier(Parser):
    uri = ctx


class Person(Parser):
    suffix = ParseName(ctx).suffix
    family_name = ParseName(ctx).last
    given_name = ParseName(ctx).first
    additional_name = ParseName(ctx).middle


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class CreativeWork(Parser):
    title = RunPython('get_sanitized', ctx.citation_title)
    description = RunPython('get_sanitized', ctx.description)
    identifiers = Concat(
        Map(Delegate(WorkIdentifier), ctx.citation_abstract_html_url),
        Map(Delegate(WorkIdentifier), OneOf(IRI(ctx.citation_doi), Static(None))),
        Map(Delegate(WorkIdentifier), ctx.citation_pdf_url),
        Map(Delegate(WorkIdentifier), ctx.id),
        Map(Delegate(WorkIdentifier), ctx.url)
    )

    related_agents = Map(Delegate(Contributor), ctx.citation_author)

    tags = Map(Delegate(ThroughTags), RunPython('get_tags', ctx.citation_keywords))
    date_published = OneOf(ParseDate(ctx.citation_publication_date), Static(None))
    subjects = Map(Delegate(ThroughSubjects), ctx.code)

    class Extra:
        date_online = OneOf(ParseDate(ctx.citation_online_date), Static(None))
        doi = OneOf(IRI(ctx.citation_doi), Static(None))

    def get_tags(self, string):
        return string.lower().split(',')

    def get_sanitized(self, string):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', string)
        return cleantext
