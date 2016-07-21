import re

from share.normalize import *
from share.normalize.utils import format_doi_as_url


class Organization(Parser):
    name = ctx.name


class Affiliation(Parser):
    pass


class Email(Parser):
    email = ctx
    is_primary = Static(False)


class PersonEmail(Parser):
    email = Delegate(Email, ctx)


class Identifier(Parser):
    base_url = Static('https://orcid.org/')
    url = ctx


class ThroughIdentifiers(Parser):
    identifier = Delegate(Identifier, ctx)


class Person(Parser):
    given_name = ParseName(ctx.name).first
    family_name = ParseName(ctx.name).last
    additional_name = ParseName(ctx.name).middle
    suffix = ParseName(ctx.name).suffix
    identifiers = Map(Delegate(ThroughIdentifiers), Maybe(ctx, 'orcid'))
    emails = Map(Delegate(PersonEmail), Maybe(ctx, 'email'))
    affiliations = Map(
        Delegate(Affiliation.using(entity=Delegate(Organization))),
        Maybe(ctx, 'affiliation')
    )


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.name
    person = Delegate(Person, ctx)


class Link(Parser):
    url = RunPython('format_doi', ctx)
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        return 'doi'

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class CreativeWork(Parser):

    DOE_CONTRIBUTOR_REGEX = re.compile(r'([^[]+?(?:\[.+?\])?)(?:(?<!\d);|$)')
    DOE_AFFILIATIONS_REGEX = re.compile(r'\s*\[(.*?)\]')
    DOE_EMAIL_REGEX = re.compile(r'((?:,? (?:Email|email|E-mail|e-mail):\s*)?(\S*@\S*))')
    DOE_ORCID_REGEX = re.compile(r'(\(ORCID:\s*(\S*)\))')

    def doe_process_contributors(self, ctx):
        return [
            self.doe_name_parser(name)
            for name
            in self.DOE_CONTRIBUTOR_REGEX.findall(ctx)
            if name
        ]

    def doe_name_parser(self, name):
        if name.strip() == 'None':
            return {'name': ''}
        name, orcid = self.extract_and_replace_one(name, self.DOE_ORCID_REGEX)
        name, email = self.extract_and_replace_one(name, self.DOE_EMAIL_REGEX)
        name, affiliations = self.doe_extract_affiliations(name)

        parsed_name = self.doe_parse_name(name)
        if affiliations:
            parsed_name['affiliation'] = list(map(self.doe_parse_affiliation, affiliations))
        if orcid:
            parsed_name['orcid'] = orcid
        if email:
            parsed_name['email'] = email
        return parsed_name

    def doe_extract_affiliations(self, name):
        affiliations = self.DOE_AFFILIATIONS_REGEX.findall(name)
        for affiliation in affiliations:
            name = name.replace('[{}]'.format(affiliation), '')
        return name, affiliations

    def doe_parse_affiliation(self, affiliation):
        return {'name': affiliation}

    def doe_parse_name(self, name):
        return {'name': name}

    def extract_and_replace_one(self, text, pattern):
        matches = pattern.findall(text)
        if matches and len(matches) == 1:
            return text.replace(matches[0][0], ''), matches[0][1]
        return text, None

    title = ctx.record['dc:title']
    description = ctx.record['dc:description']
    language = ParseLanguage(ctx.record['dc:language'])
    rights = Maybe(ctx.record, 'dc:rights')
    contributors = Map(
        Delegate(Contributor),
        RunPython('doe_process_contributors', ctx.record['dc:creator'])
    )
    links = Map(
        Delegate(ThroughLinks),
        Maybe(ctx.record, 'dc:doi')
    )
    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.record['dcq:publisher']
    )

    class Extra:
        coverage = ctx.record['dc:coverage']
        date = ctx.record['dc:date']
        date_entry = ctx.record['dc:dateEntry']
        format = ctx.record['dc:format']
        identifier = ctx.record['dc:identifier']
        identifier_citation = ctx.record['dcq:identifier-citation']
        identifier_doe_contract = ctx.record['dcq:identifierDOEcontract']
        identifier_purl = ctx.record['dcq:identifier-purl']
        identifier_other = ctx.record['dc:identifierOther']
        identifier_report = ctx.record['dc:identifierReport']
        publisher_availability = ctx.record['dcq:publisherAvailability']
        publisher_country = ctx.record['dcq:publisherCountry']
        publisher_research = ctx.record['dcq:publisherResearch']
        publisher_sponsor = ctx.record['dcq:publisherSponsor']
        relation = ctx.record['dc:relation']
        type = ctx.record['dc:type']
        type_qualifier = ctx.record['dcq:typeQualifier']
