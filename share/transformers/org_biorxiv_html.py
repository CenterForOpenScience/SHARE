import re

from share.transform.chain import *  # noqa
from share.transform.chain.soup import Soup, SoupXMLTransformer


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class Tag(Parser):
    name = ctx


class Subject(Parser):
    name = ctx


class AffiliatedAgent(Parser):
    schema = GuessAgentType(ctx, default='Organization')
    name = ctx


class Organization(Parser):
    name = ctx


class IsAffiliatedWith(Parser):
    related = Delegate(AffiliatedAgent, ctx)


class Publisher(Parser):
    agent = Delegate(Organization, ctx)


class Person(Parser):
    name = ctx.name
    identifiers = Map(Delegate(AgentIdentifier), ctx.identifiers)
    related_agents = Map(Delegate(IsAffiliatedWith), ctx.institutions)


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx['#text'])


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Creator(Parser):
    cited_as = ctx.name
    order_cited = ctx('index')
    agent = Delegate(Person, ctx)


class Preprint(Parser):
    title = Soup(ctx, 'meta', {'name': 'DC.Title'})['@content']
    description = Soup(ctx, 'meta', {'name': 'DC.Description'})['@content']
    is_deleted = Static(False)

    date_updated = ParseDate(Soup(ctx, 'meta', {'name': 'DC.Date'})['@content'])
    date_published = ParseDate(Soup(ctx, 'meta', {'name': 'citation_publication_date'})['@content'])

    rights = Soup(ctx, 'meta', {'name': 'DC.Rights'})['@content']

    identifiers = Map(
        Delegate(WorkIdentifier),
        Soup(ctx, 'meta', {'name': 'og:url'})['@content'],
        Soup(ctx, 'meta', {'name': 'DC.Identifier'})['@content'],
    )

    subjects = Map(Delegate(ThroughSubjects), Subjects(Map(ctx['#text'], Soup(ctx, **{'class': 'highwire-article-collection-term'}))))

    tags = Map(Delegate(ThroughTags), Soup(ctx, **{'class': 'highwire-article-collection-term'}))

    related_agents = Concat(
        Map(
            Delegate(Creator),
            RunPython(
                'parse_creators',
                Soup(ctx, 'meta', {'name': re.compile('^citation_author')})
            )
        ),
        Delegate(Publisher, Soup(ctx, 'meta', {'name': 'citation_publisher'})['@content'])
    )

    def parse_creators(self, soup):
        # Creators and their related information comes in as:
        # Person 1
        # Person 1's Email
        # Person 2
        # Person 2's affiliation
        # Person 2's Orcid
        # Etc, Etc
        creators = []
        for match in soup:
            if match['@name'] == 'citation_author':
                creators.append({'name': match['@content'], 'identifiers': [], 'institutions': []})
            elif match['@name'] == 'citation_author_institution':
                creators[-1]['institutions'].extend(match['@content'].split(';'))
            elif match['@name'] in ('citation_author_email', 'citation_author_orcid'):
                creators[-1]['identifiers'].append(match['@content'])
            else:
                raise ValueError('Unknown @name "{}"'.format(match['@name']))
        return creators


class BiorxivHTMLTransformer(SoupXMLTransformer):
    VERSION = 1

    root_parser = Preprint
