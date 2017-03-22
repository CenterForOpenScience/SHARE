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
        location = Try(ctx['publisher']['publisher-loc']['#text'])


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
    name = OneOf(
        Soup(ctx, 'institution', **{'content-type': None})['#text'],
        Soup(ctx, 'institution', **{'content-type': None})[-1]['#text'],
        Soup(ctx, 'institution')['#text'],
        Soup(ctx, 'institution')[-1]['#text'],
    )

    class Extra:
        addr_line = Try(ctx['addr-line']['#text'])
        city = Try(ctx['city']['#text'])
        country = Try(ctx.country['#text'])


class IsAffiliatedWith(Parser):
    related = Delegate(Institution, ctx)


class Person(Parser):
    family_name = ctx.name['surname']['#text']
    given_name = ctx.name['given-names']['#text']

    identifiers = Map(Delegate(AgentIdentifier), Soup(ctx, 'contrib-id', **{'contrib-id-type': None}), ctx.email)

    related_agents = Map(
        Delegate(IsAffiliatedWith),
        RunPython('get_affiliations', Soup(ctx, 'xref', **{'ref-type': 'aff'}))
    )

    def get_affiliations(self, refs):
        if not isinstance(refs, list):
            refs = [refs]
        return [
            SoupXMLDict(soup=ctx.frames[0]['context'].soup.find(id=ref['@rid']))
            for ref in refs
            if ref
        ]


class Consortium(Parser):
    name = ctx.collab['#text']


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
    description = Try(Soup(ctx.article.front['article-meta'], 'abstract', **{'abstract-type': None})['#text'])
    is_deleted = Static(False)

    date_published = ParseDate(RunPython('make_date', Soup(ctx.article.front['article-meta'], 'pub-date', **{'publication-format': 'electronic'})))
    date_updated = ParseDate(RunPython('make_date', Soup(ctx.article.front['article-meta'], 'pub-date', **{'publication-format': 'electronic'})))
    rights = IRI(ctx.article.front['article-meta']['license']['@xlink:href'])

    identifiers = Map(
        Delegate(WorkIdentifier),
        Soup(ctx.article.front['article-meta'], 'article-id', **{'pub-id-type': 'doi'})['#text'],
    )

    subjects = Map(
        Delegate(ThroughSubjects),
        Subjects(Map(ctx['#text'], ctx.article.front['article-meta']['article-categories']['subject']))
    )

    tags = Map(
        Delegate(ThroughTags),
        Concat(
            ctx.article.front['article-meta']['article-categories']['subject'],
            Map(ctx.kwd, ctx.article.front['article-meta']['kwd-group']),
            deep=True
        ),
    )

    related_agents = Concat(
        Map(Delegate(Funder), Try(ctx.article.front['article-meta']['funding-group']['award-group'])),
        Map(Delegate(Publisher), ctx.article.front['journal-meta']),
        Map(Delegate(Creator), Filter(lambda x: x.collab is None, Concat(Map(ctx.contrib, ctx.article.front['article-meta']['contrib-group']), deep=True))),
        Map(Delegate(Creator.using(agent=Delegate(Consortium), cited_as=ctx.collab['#text'])), Filter(lambda x: x.collab is not None, Concat(Map(ctx.contrib, ctx.article.front['article-meta']['contrib-group']), deep=True))),
    )

    class Extra:
        executive_summary = Try(Soup(ctx.article.front['article-meta'], 'abstract', **{'abstract-type': 'executive-summary'})['#text'])

    def make_date(self, obj):
        return '{}-{}-{}'.format(obj.year['#text'], obj.month['#text'], obj.day['#text'])


class ElifeTransformer(SoupXMLTransformer):
    VERSION = 1
    root_parser = Article
