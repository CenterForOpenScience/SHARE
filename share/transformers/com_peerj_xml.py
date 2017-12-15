from share.transform.chain import *  # noqa
from share.transform.chain.soup import Soup, SoupXMLDict, SoupXMLTransformer


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class AgentIdentifier(Parser):
    uri = IRI(ctx['#text'])


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx['#text'])


class PublisherOrganization(Parser):
    schema = 'Organization'  # TODO Switch to OAI schema picker

    name = ctx['publisher']['publisher-name']['#text']
    identifiers = Map(Delegate(AgentIdentifier), Soup(ctx, 'issn', **{'pub-type': 'epub'}))

    class Extra:
        location = ctx['publisher']['publisher-loc']['#text']


class Publisher(Parser):
    agent = Delegate(PublisherOrganization, ctx)


class FunderOrganization(Parser):
    schema = 'Organization'  # TODO Switch to OAI schema picker
    name = ctx


class Funder(Parser):
    agent = Delegate(FunderOrganization, ctx['funding-source']['#text'])

    class Extra:
        award_id = Map(ctx['#text'], ctx['award-id'])


class Institution(Parser):
    name = ctx.institution['#text']

    class Extra:
        addr_line = Try(ctx['addr-line']['#text'])
        city = Try(ctx['city']['#text'])
        country = ctx.country['#text']


class IsAffiliatedWith(Parser):
    related = Delegate(Institution, ctx)


class Person(Parser):
    family_name = ctx.name['surname']['#text']
    given_name = ctx.name['given-names']['#text']

    identifiers = Map(Delegate(AgentIdentifier), ctx['contrib-id'], ctx.email)

    related_agents = Map(
        Delegate(IsAffiliatedWith),
        RunPython('get_affiliations', ctx.xref)
    )

    def get_affiliations(self, refs):
        if not isinstance(refs, list):
            refs = [refs]
        return [
            SoupXMLDict(soup=ctx.frames[0]['context'].soup.find(id=ref['@rid']))
            for ref in refs
            if ref
        ]


class Contributor(Parser):
    agent = Delegate(Person, ctx)
    cited_as = Join(Concat(ctx.name['given-names']['#text'], ctx.name['surname']['#text']))

    class Extra:
        contributions = RunPython('get_contributions', ctx)

    def get_contributions(self, context):
        return [
            x.parent.text
            for x in
            ctx.frames[0]['context'].soup.find_all(**{'ref-type': 'contrib', 'rid': context.soup.attrs.get('@id')})
        ]


class Creator(Contributor):
    order_cited = ctx('index')


class Article(Parser):
    title = ctx.article.front['article-meta']['title-group']['article-title']['#text']
    description = ctx.article.front['article-meta'].abstract['#text']
    is_deleted = Static(False)

    date_published = ParseDate(ctx.article.front['article-meta']['pub-date']['@iso-8601-date'])
    date_updated = ParseDate(ctx.article.front['article-meta']['pub-date']['@iso-8601-date'])
    # free_to_read_type = IRI(ctx.article.front['article-meta']['license']['@xlink:href'])
    # free_to_read_date =
    rights = IRI(ctx.article.front['article-meta']['license']['@xlink:href'])

    identifiers = Map(
        Delegate(WorkIdentifier),
        ctx.article.front['article-meta']['self-uri']['@xlink:href'],
        Soup(ctx.article.front['article-meta'], 'article-id', **{'pub-id-type': 'doi'})['#text'],
    )

    subjects = Map(
        Delegate(ThroughSubjects),
        Subjects(Map(ctx['#text'], ctx.article.front['article-meta']['article-categories']['subject']))
    )

    tags = Map(
        Delegate(ThroughTags),
        ctx.article.front['article-meta']['article-categories']['subject'],
        ctx.article.front['article-meta']['kwd-group']['kwd'],
    )

    related_agents = Concat(
        Map(Delegate(Funder), ctx.article.front['article-meta']['funding-group']['award-group']),
        Map(Delegate(Publisher), ctx.article.front['journal-meta']),
        Map(Delegate(Creator), Soup(ctx.article.front['article-meta'], 'contrib-group', **{'content-type': 'authors'}).contrib),
        Map(Delegate(Contributor), Try(Soup(ctx.article.front['article-meta'], 'contrib-group', **{'content-type': lambda x: x != 'authors'}).contrib)),
    )

    # TODO Maybe process references as well?
    # related_works = Concat(
    # )

    class Extra:
        funding_statement = ctx.article.front['article-meta']['funding-group']['funding-statement']['#text']


class Preprint(Article):
    pass


class PeerJXMLTransformer(SoupXMLTransformer):
    VERSION = 1

    def get_root_parser(self, unwrapped, emitted_type=None, **kwargs):
        if emitted_type == 'preprint':
            return Preprint
        return Article
