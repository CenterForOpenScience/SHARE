import re

from share.legacy_normalize.transform.chain import *


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Organization(Parser):
    schema = GuessAgentType(ctx)
    name = ctx


class IsAffiliatedWith(Parser):
    related = Delegate(Organization, ctx)


class Person(Parser):
    name = ctx.name
    identifiers = Map(Delegate(AgentIdentifier), ctx.identifiers)
    related_agents = Map(Delegate(IsAffiliatedWith), ctx.institutions)


class Creator(Parser):
    order_cited = ctx('index')
    cited_as = ctx.name
    agent = Delegate(Person, ctx)


class Contributor(Parser):
    agent = Delegate(Organization, ctx)


class Funder(Parser):
    agent = Delegate(Organization, ctx)


class Publisher(Parser):
    agent = Delegate(Organization, ctx)


class CreativeWork(Parser):
    DOE_CONTRIBUTOR_REGEX = re.compile(r'((.+?)(?:, E-mail: [^,\s]+)*(?: \[.+?\])?(?: \(ORCID:.{16}\))?(?:;|$))', re.IGNORECASE)
    DOE_AFFILIATIONS_REGEX = re.compile(r'\s*\[(.*?)\]')
    DOE_EMAIL_REGEX = re.compile(r'(?:,? E-?mail:\s*)?(\S+@\S+?\.\S+)', re.IGNORECASE)
    DOE_ORCID_REGEX = re.compile(r'\(ORCID:\s*(\S*)\)')

    schema = RunPython('get_schema', ctx.record['dc:type'])

    title = ctx.record['dc:title']
    description = ctx.record['dc:description']
    # is_deleted
    date_published = Try(ParseDate(ctx.record['dc:date']), exceptions=(InvalidDate, ))
    date_updated = OneOf(
        ParseDate(ctx.record['dc:dateentry']),
        ParseDate(ctx.record['dc:date']),
        Static(None)
    )
    # free_to_read_type
    # free_to_read_date
    rights = Maybe(ctx.record, 'dc:rights')
    language = ParseLanguage(ctx.record['dc:language'])

    tags = Map(Delegate(ThroughTags), RunPython('get_tags', ctx.record['dc:subject']))

    identifiers = Map(
        Delegate(WorkIdentifier),
        Try(ctx.record['dc:doi']),
        ctx.record['dcq:identifier-citation'],
        Try(ctx.record['dcq:identifier-purl']['#text']),
    )
    related_agents = Concat(
        Map(Delegate(Publisher), RunPython(lambda x: x.split(', ') if x else None, ctx.record['dcq:publisher'])),
        Map(Delegate(Funder), RunPython(lambda x: x.split(', ') if x else None, ctx.record['dcq:publisherSponsor'])),
        Map(Delegate(Contributor), RunPython(lambda x: x.split(', ') if x else None, ctx.record['dcq:publisherResearch'])),
        Map(Delegate(Creator), RunPython('get_contributors', ctx.record['dc:creator'])),
    )

    class Extra:
        coverage = ctx.record['dc:coverage']
        format = ctx.record['dc:format']
        identifier = ctx.record['dc:identifier']
        identifier_doe_contract = ctx.record['dcq:identifierDOEcontract']
        identifier_other = ctx.record['dc:identifierOther']
        identifier_report = ctx.record['dc:identifierReport']
        publisher_availability = ctx.record['dcq:publisherAvailability']
        publisher_country = ctx.record['dcq:publisherCountry']
        relation = ctx.record['dc:relation']
        type_qualifier = ctx.record['dcq:typeQualifier']

    def get_schema(self, type):
        return {
            'Thesis/Dissertation': 'Thesis',
            'Technical Report': 'Report',
            'Journal Article': 'Article',
            'Patent': 'Patent',
            None: 'CreativeWork',
            'Miscellaneous': 'CreativeWork',
            'Other': 'CreativeWork',
            'Program Document': 'CreativeWork',
            'Conference': 'ConferencePaper',
            'Dataset': 'DataSet',
            'Book': 'Book',
        }[type].lower()

    def get_tags(self, tags):
        return (tags or '').split('; ')

    def get_contributors(self, context):
        contributors = []
        for (match, name) in self.DOE_CONTRIBUTOR_REGEX.findall(context or ''):
            if not match or not name:
                continue
            contributors.append({
                'name': name.strip(),
                'institutions': self.DOE_AFFILIATIONS_REGEX.findall(match),
                'identifiers': self.DOE_EMAIL_REGEX.findall(match) + self.DOE_ORCID_REGEX.findall(match)
            })
        return contributors


class ScitechTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
