from share.normalize import Parser, Delegate, RunPython, ParseName, ParseDate, Map, ctx, Try


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

# The subject field is not helpful on Philica. It says "See abstract"
# class Subjects(Parser):
#     name = ctx
#
#
# class ThroughSubjects(Parser):
#     subject = Delegate(Subjects, ctx)
#


class Association(Parser):
    pass


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Preprint(Parser):
    title = Try(ctx.data['DC.title'])
    description = Try(ctx.data['DC.description'])
    date_published = ParseDate(ctx.data['DC.created'])
    contributors = Map(Delegate(Contributor), ctx.data['DC.contributor'])
    links = Map(Delegate(ThroughLinks), ctx.data['href'], ctx.data['DC.source'])
    publishers = Map(Delegate(Association.using(entity=Delegate(Publisher))), ctx.data['DC.publisher'])
    language = ctx.data['DC.language']
    rights = ctx.data['DC.rights']

    class Extra:
        abstract = ctx.data['DC.abstract']
        coverage = ctx.data['DC.coverage']
        data_created = ParseDate(ctx.data['DC.created'])
        data_submitted = ParseDate(ctx.data['DC.dateSubmitted'])
        identifiers = ctx.data['DC.identifier']
        format_type = ctx.data['DC.identifier']
        type_publication = ctx.data['DC.type']
        citation = ctx.data['DC.biliographicCitation']  # Typo intended
        subjects = ctx.data['DC.subject']
