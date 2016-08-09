import re
import logging

from share.normalize import *
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


logger = logging.getLogger(__name__)

THE_REGEX = re.compile(r'(^the\s|\sthe\s)')
DATE_REGEX = re.compile(r'(^[^a-zA-Z]+$)')


def force_text(data):
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        if '#text' in data:
            return data['#text']
        raise Exception('#text is not in {}'.format(data))
    if isinstance(data, list):
        for item in data:
            try:
                return force_text(item)
            except Exception:
                pass
        raise Exception('No value in list {} is a string.'.format(data))
    raise Exception('{} is not a string or a dictionary.'.format(data))


class Link(Parser):
    url = RunPython(
        'format_link',
        RunPython(
            force_text,
            ctx
        )
    )
    type = Static('doi')

    def format_link(self, link):
        return format_doi_as_url(self, link)


class AlternateLink(Parser):
    schema = 'Link'

    url = RunPython(
        force_text,
        ctx
    )
    type = Static('misc')


class RelatedLink(Parser):
    schema = 'Link'

    url = RunPython(
        force_text,
        ctx
    )
    type = RunPython('lower', Try(ctx['@relatedIdentifierType']))

    def lower(self, type):
        return type.lower()


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class ThroughAlternateLinks(Parser):
    schema = 'ThroughLinks'

    link = Delegate(AlternateLink, ctx)


class ThroughRelatedLinks(Parser):
    schema = 'ThroughLinks'

    link = Delegate(RelatedLink, ctx)


class Affiliation(Parser):
    pass


class ContributorInstitution(Parser):
    schema = 'Institution'

    name = ctx.contributorName

    class Extra:
        contributor_type = Try(ctx.contributorType)


class ContributorOrganization(Parser):
    schema = 'Organization'

    name = ctx.contributorName

    class Extra:
        contributor_type = Try(ctx.contributorType)


class CreatorInstitution(Parser):
    schema = 'Institution'

    name = ctx.creatorName


class CreatorOrganization(Parser):
    schema = 'Organization'

    name = ctx


class Identifier(Parser):
    base_url = Try(ctx['@schemeURI'])
    url = Join(Concat(Try(ctx['@schemeURI']), Try(ctx['#text'])), joiner='/')


class ThroughIdentifiers(Parser):
    identifier = Delegate(Identifier, ctx)


class ContributorPerson(Parser):
    schema = 'Person'

    suffix = ParseName(ctx.contributorName).suffix
    family_name = ParseName(ctx.contributorName).last
    given_name = ParseName(ctx.contributorName).first
    additional_name = ParseName(ctx.contributorName).middle
    identifiers = Map(Delegate(ThroughIdentifiers), Concat(Try(ctx, 'nameIdentifier')))

    class Extra:
        name_identifier = Try(
            RunPython(
                force_text,
                ctx.nameIdentifier
            )
        )
        name_identifier_scheme = Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = Try(ctx.nameIdentifier['@schemeURI'])
        contributor_type = Try(ctx.contributorType)


class CreatorPerson(Parser):
    schema = 'Person'

    suffix = ParseName(ctx.creatorName).suffix
    family_name = ParseName(ctx.creatorName).last
    given_name = ParseName(ctx.creatorName).first
    additional_name = ParseName(ctx.creatorName).middle
    affiliations = Map(Delegate(Affiliation.using(entity=Delegate(CreatorOrganization))), Concat(Try(
        RunPython(
            force_text,
            ctx.affiliation
        )
    )))
    identifiers = Map(Delegate(ThroughIdentifiers), Concat(Try(ctx, 'nameIdentifier')))

    class Extra:
        name_identifier = Try(
            RunPython(
                force_text,
                ctx.nameIdentifier
            )
        )
        name_identifier_scheme = Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = Try(ctx.nameIdentifier['@schemeURI'])


class Contributor(Parser):
    person = Delegate(ContributorPerson, ctx)
    cited_name = Try(ctx.contributorName)
    order_cited = ctx('index')


class Creator(Parser):
    schema = 'Contributor'

    person = Delegate(CreatorPerson, ctx)
    cited_name = Try(ctx.creatorName)
    order_cited = ctx('index')


class Funder(Parser):
    community_identifier = Join(Concat(Try(ctx.nameIdentifier['@schemeURI']), Try(ctx.nameIdentifier['#text'])), joiner='/')

    class Extra:
        name = Try(ctx.contributorName)
        name_identifier_scheme = Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = Try(ctx.nameIdentifier['@schemeURI'])


class Venue(Parser):
    name = Try(
        RunPython(
            force_text,
            ctx.geoLocationPlace
        )
    )
    # polygon = Try(ctx.geoLocationBox)
    # point = Try(ctx.geoLocationPoint)

    class Extra:
        polygon = Try(ctx.geoLocationBox)
        point = Try(ctx.geoLocationPoint)


class ThroughVenues(Parser):
    venue = Delegate(Venue, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class CreativeWork(Parser):

    # Schema definitions: http://schema.datacite.org/meta/kernel-3.1/doc/DataCite-MetadataKernel_v3.1.pdf

    PEOPLE_TYPES = (
        'ContactPerson',
        'DataCurator',
        'Editor',
        'ProjectLeader',
        'ProjectManager',
        'ProjectMember',
        'RelatedPerson',
        'Researcher',
        'Supervisor',
        'WorkPackageLeader'
    )
    CHECK_TYPES = (
        'DataCollector',
        'DataManager',
        'Producer',
        'RightsHolder',
        'Sponsor',
        'Other'
    )

    NOT_PEOPLE_TYPES = (
        'Distributor',
        'HostingInstitution',
        'RegistrationAgency',
        'RegistrationAuthority',
        'ResearchGroup'
    )

    ORGANIZATION_KEYWORDS = (
        THE_REGEX,
        'council',
        'center',
        'foundation'
    )
    INSTITUTION_KEYWORDS = (
        'school',
        'university',
        'institution',
        'college',
        'institute'
    )

    title = RunPython(
        force_text,
        Try(ctx.record.metadata['oai_datacite'].payload.resource.titles.title)
    )
    description = RunPython(
        force_text,
        Try(ctx.record.metadata['oai_datacite'].payload.resource.descriptions.description[0])
    )

    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        Try(ctx.record.metadata['oai_datacite'].payload.resource.publisher)
    )

    rights = Try(
        Join(
            RunPython(
                'text_list',
                Concat(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights)
            )
        )
    )

    language = ParseLanguage(Try(ctx.record.metadata['oai_datacite'].payload.resource.language))

    contributors = Concat(
        Map(
            Delegate(Creator),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'contributor',
                'creator'
            )
        ),
        Map(
            Delegate(Contributor),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'contributor',
                'contributor'
            )
        )
    )

    institutions = Concat(
        Map(
            Delegate(Association.using(entity=Delegate(CreatorInstitution))),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'institution',
                'creator'
            )
        ),
        Map(
            Delegate(Association.using(entity=Delegate(ContributorInstitution))),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'institution',
                'contributor'
            )
        )
    )

    organizations = Concat(
        Map(
            Delegate(Association.using(entity=Delegate(CreatorOrganization))),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'organization',
                'creator'
            )
        ),
        Map(
            Delegate(Association.using(entity=Delegate(ContributorOrganization))),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'organization',
                'contributor'
            )
        )
    )

    tags = Map(
        Delegate(ThroughTags),
        RunPython(
            force_text,
            Concat(
                Maybe(Maybe(ctx.record, 'metadata')['oai_datacite'], 'type'),
                RunPython(
                    'text_list',
                    (Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.subjects.subject)))
                ),
                Try(ctx.record.metadata['oai_datacite'].payload.resource.formats.format),
                Try(ctx.record.metadata['oai_datacite'].datacentreSymbol),
                Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType['#text']),
                Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType['@resourceTypeGeneral']),
                Maybe(ctx.record.header, 'setSpec'),
                Maybe(ctx.record.header, '@status')
            )
        )
    )

    links = Concat(
        Map(
            Delegate(ThroughLinks),
            Concat(
                Try(ctx.record.metadata['oai_datacite'].payload.resource.identifier)
            )
        ),
        Map(
            Delegate(ThroughAlternateLinks),
            Concat(
                Try(ctx.record.metadata['oai_datacite'].payload.resource.alternateIdentifiers.alternateidentifier)
            )
        ),
        Map(
            Delegate(ThroughRelatedLinks),
            Concat(
                Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)
            )
        )
    )

    date_updated = ParseDate(ctx.record.header.datestamp)
    date_created = ParseDate(RunPython('get_date_type', Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Created'))
    date_published = ParseDate(RunPython('get_date_type', Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Issued'))
    free_to_read_type = Try(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights['@rightsURI'])
    free_to_read_date = ParseDate(RunPython('get_date_type', Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Available'))
    funders = Map(
        Delegate(Association.using(entity=Delegate(Funder))),
        RunPython(
            'get_contributors',
            Concat(Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
            'funder',
            'contributor'
        )
    )
    venues = Map(
        Delegate(ThroughVenues),
        Try(ctx.record.metadata['oai_datacite'].payload.resource.geoLocations.geoLocation)
    )

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        status = Maybe(ctx.record.header, '@status')

        datestamp = ParseDate(ctx.record.header.datestamp)

        set_spec = Maybe(ctx.record.header, 'setSpec')

        is_reference_quality = Try(ctx.record.metadata['oai_datacite'].isReferenceQuality)

        schema_version = Try(ctx.record.metadata['oai_datacite'].schemaVersion)

        datacentre_symbol = Try(ctx.record.metadata['oai_datacite'].datacentreSymbol)

        identifiers = Try(ctx.record.metadata['oai_datacite'].payload.resource.identifier)

        alternate_identifiers = Try(ctx.record.metadata['oai_datacite'].payload.resource.alternateIdentifiers.alternateidentifier)

        titles = Try(ctx.record.metadata['oai_datacite'].payload.resource.titles.title)

        publisher = Try(ctx.record.metadata['oai_datacite'].payload.resource.publisher)

        publication_year = Try(ctx.record.metadata['oai_datacite'].payload.resource.publicationYear)

        subject = Try(ctx.record.metadata['oai_datacite'].payload.resource.subjects.subject)

        resourceType = Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType)

        sizes = Try(ctx.record.metadata['oai_datacite'].payload.resource.size)

        format_type = Try(ctx.record.metadata['oai_datacite'].payload.resource.formats.format)

        version = Try(ctx.record.metadata['oai_datacite'].payload.resource.version)

        rights = Try(ctx.record.metadata['oai_datacite'].payload.resource.rights)

        rightsList = Try(ctx.record.metadata['oai_datacite'].payload.resource.rightsList)

        related_identifiers = Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)

        description = Try(ctx.record.metadata['oai_datacite'].payload.resource.descriptions)

        dates = Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)

        contributors = Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)

        creators = Try(ctx.record.metadata['oai_datacite'].payload.resource.creators)

        geolocations = Try(ctx.record.metadata['oai_datacite'].payload.resource.geoLocations)

    def get_date_type(self, date_obj, date_type):
        try:
            date = None
            for obj in date_obj:
                if obj['@dateType'] == date_type:
                    date = obj['#text']
            if date and not DATE_REGEX.search(date):
                return None
        except KeyError:
            return None
        return date

    def text_list(self, data):
        text_list = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if '#text' in item:
                        text_list.append(item['#text'])
                        continue
                elif isinstance(item, str):
                    text_list.append(item)
                    continue
                logger.warning('#text is not in {} and it is not a string'.format(item))
            return text_list
        else:
            raise Exception('{} is not a list.'.format(data))

    def get_contributors(self, options, entity, field=None):
        """
        Returns list of organization, institutions, or contributors names based on entity type.
        """
        if entity == 'organization':
            organizations = []
            for value in options:
                val = self.try_contributor_type(value, self.NOT_PEOPLE_TYPES)
                if val:
                    if field == 'creator':
                        organizations.append(val[field + 'Name'])
                    else:
                        organizations.append(val)
                elif (
                    value[field + 'Name'] and
                    not self.list_in_string(value[field + 'Name'], self.INSTITUTION_KEYWORDS) and
                    self.list_in_string(value[field + 'Name'], self.ORGANIZATION_KEYWORDS)
                ):
                    if field == 'creator':
                        organizations.append(value[field + 'Name'])
                    else:
                        organizations.append(value)

            return organizations
        elif entity == 'institution':
            institutions = []
            for value in options:
                val = self.try_contributor_type(value, self.NOT_PEOPLE_TYPES)
                if val:
                    institutions.append(val)
                elif (
                    value[field + 'Name'] and
                    self.list_in_string(value[field + 'Name'], self.INSTITUTION_KEYWORDS)
                ):
                    institutions.append(value)

            return institutions
        elif entity == 'contributor':
            people = []
            for value in options:
                val = self.try_contributor_type(value, self.PEOPLE_TYPES)
                if val:
                    people.append(val)
                elif (
                    value[field + 'Name'] and
                    not self.list_in_string(value[field + 'Name'], self.INSTITUTION_KEYWORDS) and not
                    self.list_in_string(value[field + 'Name'], self.ORGANIZATION_KEYWORDS)
                ):
                    people.append(value)
            return people
        elif entity == 'funder':
            funders = []
            for value in options:
                val = self.try_contributor_type(value, ['Funder'])
                if val:
                    funders.append(val)
            return funders
        else:
            return options

    def try_contributor_type(self, value, target_list_types):
        try:
            contrib_type_item = value['@contributorType']
            if contrib_type_item in target_list_types:
                return value
            return None
        except KeyError:
            return None

    def list_in_string(self, string, list_):
        for word in list_:
            if isinstance(word, str):
                if word in string.lower():
                    return True
            else:
                if word.search(string):
                    return True
        return False
