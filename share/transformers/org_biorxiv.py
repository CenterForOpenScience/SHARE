import itertools

from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser


class AgentIdentifier(Parser):
    uri = tools.IRI(ctx)


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx)


class Organization(Parser):
    name = ctx


class Publisher(Parser):
    agent = tools.Delegate(Organization, ctx)


class Institution(Parser):
    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(Institution)


class Person(Parser):
    given_name = tools.ParseName(ctx.author).first
    family_name = tools.ParseName(ctx.author).last
    additional_name = tools.ParseName(ctx.author).middle
    suffix = tools.ParseName(ctx.author).suffix

    identifiers = tools.Map(tools.Delegate(AgentIdentifier, tools.Try(ctx.email)))
    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), tools.Try(ctx.institution))


class Creator(Parser):
    order_cited = ctx('index')
    agent = tools.Delegate(Person, ctx)
    cited_as = ctx.author


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
    # is_deleted
    date_published = tools.ParseDate(tools.Try(ctx['article:published_time']))
    date_updated = tools.ParseDate(tools.Try(ctx['DC.Date']))
    # free_to_read_type
    # free_to_read_date
    rights = tools.Try(ctx['DC.Rights'])
    language = tools.Try(ctx['DC.Language'])

    subjects = tools.Map(tools.Delegate(ThroughSubjects), tools.Static('Biology'), tools.Subjects(tools.Try(ctx['subject-areas'])))
    tags = tools.Map(tools.Delegate(ThroughTags), tools.Try(ctx['category']), tools.Try(ctx['subject-areas']))

    identifiers = tools.Map(tools.Delegate(WorkIdentifier), tools.Try(ctx['og:url']), ctx['citation_public_url'], ctx['citation_doi'])

    related_agents = tools.Concat(
        tools.Map(tools.Delegate(Publisher), tools.Try(ctx['DC.Publisher'])),
        tools.Map(tools.Delegate(Creator), tools.RunPython('get_contributors', ctx))
    )
    # related_works

    class Extra:
        identifiers = ctx['DC.Identifier']
        access_rights = ctx['DC.AccessRights']

    def get_contributors(self, link):
        authors = link.get('citation_author', []) if isinstance(link.get('citation_author', []), list) else [link['citation_author']]
        institutions = link.get('citation_author_institution', []) if isinstance(link.get('citation_author_institution', []), list) else [link['citation_author_institution']]
        emails = link.get('citation_author_email', []) if isinstance(link.get('citation_author_email', []), list) else [link['citation_author_email']]

        contribs = []
        for author, email, institution in itertools.zip_longest(authors, emails, institutions):
            contrib = {
                'author': author,
                'institution': institution,
                'email': email,
            }
            contribs.append(contrib)

        return contribs


class BiorxivTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
