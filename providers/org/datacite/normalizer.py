import re
import logging

from share.normalize import ctx, tools
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
    url = tools.RunPython(
        'format_link',
        tools.RunPython(
            force_text,
            ctx
        )
    )
    type = tools.Static('doi')

    def format_link(self, link):
        return format_doi_as_url(self, link)


class AlternateLink(Parser):
    schema = 'Link'

    url = tools.RunPython(
        force_text,
        ctx
    )
    type = tools.Static('misc')


class RelatedLink(Parser):
    schema = 'Link'

    url = tools.RunPython(
        force_text,
        ctx
    )
    type = tools.RunPython('lower', tools.Try(ctx['@relatedIdentifierType']))

    def lower(self, type):
        return type.lower()


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class ThroughAlternateLinks(Parser):
    schema = 'ThroughLinks'

    link = tools.Delegate(AlternateLink, ctx)


class ThroughRelatedLinks(Parser):
    schema = 'ThroughLinks'

    link = tools.Delegate(RelatedLink, ctx)


class Affiliation(Parser):
    pass


class ContributorInstitution(Parser):
    schema = 'Institution'

    name = ctx.contributorName

    class Extra:
        contributor_type = tools.Try(ctx.contributorType)


class ContributorOrganization(Parser):
    schema = 'Organization'

    name = ctx.contributorName

    class Extra:
        contributor_type = tools.Try(ctx.contributorType)


class CreatorInstitution(Parser):
    schema = 'Institution'

    name = ctx.creatorName


class CreatorOrganization(Parser):
    schema = 'Organization'

    name = ctx


class Identifier(Parser):
    base_url = tools.Try(ctx['@schemeURI'])
    url = tools.Join(tools.Concat(tools.Try(ctx['@schemeURI']), tools.Try(ctx['#text'])), joiner='/')


class ThroughIdentifiers(Parser):
    identifier = tools.Delegate(Identifier, ctx)


class ContributorPerson(Parser):
    schema = 'Person'

    suffix = tools.ParseName(ctx.contributorName).suffix
    family_name = tools.ParseName(ctx.contributorName).last
    given_name = tools.ParseName(ctx.contributorName).first
    additional_name = tools.ParseName(ctx.contributorName).middle
    identifiers = tools.Map(tools.Delegate(ThroughIdentifiers), tools.Concat(tools.Try(ctx, 'nameIdentifier')))

    class Extra:
        name_identifier = tools.Try(
            tools.RunPython(
                force_text,
                ctx.nameIdentifier
            )
        )
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])
        contributor_type = tools.Try(ctx.contributorType)


class CreatorPerson(Parser):
    schema = 'Person'

    suffix = tools.ParseName(ctx.creatorName).suffix
    family_name = tools.ParseName(ctx.creatorName).last
    given_name = tools.ParseName(ctx.creatorName).first
    additional_name = tools.ParseName(ctx.creatorName).middle
    affiliations = tools.Map(tools.Delegate(Affiliation.using(entity=tools.Delegate(CreatorOrganization))), tools.Concat(tools.Try(
        tools.RunPython(
            force_text,
            ctx.affiliation
        )
    )))
    identifiers = tools.Map(tools.Delegate(ThroughIdentifiers), tools.Concat(tools.Try(ctx, 'nameIdentifier')))

    class Extra:
        name_identifier = tools.Try(
            tools.RunPython(
                force_text,
                ctx.nameIdentifier
            )
        )
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])


class Contributor(Parser):
    person = tools.Delegate(ContributorPerson, ctx)
    cited_name = tools.Try(ctx.contributorName)
    order_cited = ctx('index')


class Creator(Parser):
    schema = 'Contributor'

    person = tools.Delegate(CreatorPerson, ctx)
    cited_name = tools.Try(ctx.creatorName)
    order_cited = ctx('index')


class Funder(Parser):
    community_identifier = tools.Join(tools.Concat(tools.Try(ctx.nameIdentifier['@schemeURI']), tools.Try(ctx.nameIdentifier['#text'])), joiner='/')

    class Extra:
        name = tools.Try(ctx.contributorName)
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])


class Venue(Parser):
    name = tools.Try(
        tools.RunPython(
            force_text,
            ctx.geoLocationPlace
        )
    )
    # polygon = tools.Try(ctx.geoLocationBox)
    # point = tools.Try(ctx.geoLocationPoint)

    class Extra:
        polygon = tools.Try(ctx.geoLocationBox)
        point = tools.Try(ctx.geoLocationPoint)


class ThroughVenues(Parser):
    venue = tools.Delegate(Venue, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


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

    title = tools.RunPython(
        force_text,
        tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.titles.title)
    )
    description = tools.RunPython(
        force_text,
        tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.descriptions.description[0])
    )

    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.publisher)
    )

    rights = tools.Try(
        tools.Join(
            tools.RunPython(
                'text_list',
                tools.Concat(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights)
            )
        )
    )

    language = tools.ParseLanguage(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.language))

    contributors = tools.Concat(
        tools.Map(
            tools.Delegate(Creator),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'contributor',
                'creator'
            )
        ),
        tools.Map(
            tools.Delegate(Contributor),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'contributor',
                'contributor'
            )
        )
    )

    institutions = tools.Concat(
        tools.Map(
            tools.Delegate(Association.using(entity=tools.Delegate(CreatorInstitution))),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'institution',
                'creator'
            )
        ),
        tools.Map(
            tools.Delegate(Association.using(entity=tools.Delegate(ContributorInstitution))),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'institution',
                'contributor'
            )
        )
    )

    organizations = tools.Concat(
        tools.Map(
            tools.Delegate(Association.using(entity=tools.Delegate(CreatorOrganization))),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator)),
                'organization',
                'creator'
            )
        ),
        tools.Map(
            tools.Delegate(Association.using(entity=tools.Delegate(ContributorOrganization))),
            tools.RunPython(
                'get_contributors',
                tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
                'organization',
                'contributor'
            )
        )
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.RunPython(
            force_text,
            tools.Concat(
                tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oai_datacite'], 'type'),
                tools.RunPython(
                    'text_list',
                    (tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.subjects.subject)))
                ),
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.formats.format),
                tools.Try(ctx.record.metadata['oai_datacite'].datacentreSymbol),
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType['#text']),
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType['@resourceTypeGeneral']),
                tools.Maybe(ctx.record.header, 'setSpec'),
                tools.Maybe(ctx.record.header, '@status')
            )
        )
    )

    links = tools.Concat(
        tools.Map(
            tools.Delegate(ThroughLinks),
            tools.Concat(
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.identifier)
            )
        ),
        tools.Map(
            tools.Delegate(ThroughAlternateLinks),
            tools.Concat(
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.alternateIdentifiers.alternateidentifier)
            )
        ),
        tools.Map(
            tools.Delegate(ThroughRelatedLinks),
            tools.Concat(
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)
            )
        )
    )

    date_updated = tools.ParseDate(ctx.record.header.datestamp)
    date_created = tools.ParseDate(tools.RunPython('get_date_type', tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Created'))
    date_published = tools.ParseDate(tools.RunPython('get_date_type', tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Issued'))
    free_to_read_type = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights['@rightsURI'])
    free_to_read_date = tools.ParseDate(tools.RunPython('get_date_type', tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)), 'Available'))
    funders = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Funder))),
        tools.RunPython(
            'get_contributors',
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
            'funder',
            'contributor'
        )
    )
    venues = tools.Map(
        tools.Delegate(ThroughVenues),
        tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.geoLocations.geoLocation)
    )

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        status = tools.Maybe(ctx.record.header, '@status')

        datestamp = tools.ParseDate(ctx.record.header.datestamp)

        set_spec = tools.Maybe(ctx.record.header, 'setSpec')

        is_reference_quality = tools.Try(ctx.record.metadata['oai_datacite'].isReferenceQuality)

        schema_version = tools.Try(ctx.record.metadata['oai_datacite'].schemaVersion)

        datacentre_symbol = tools.Try(ctx.record.metadata['oai_datacite'].datacentreSymbol)

        identifiers = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.identifier)

        alternate_identifiers = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.alternateIdentifiers.alternateidentifier)

        titles = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.titles.title)

        publisher = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.publisher)

        publication_year = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.publicationYear)

        subject = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.subjects.subject)

        resourceType = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.resourceType)

        sizes = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.size)

        format_type = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.formats.format)

        version = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.version)

        rights = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.rights)

        rightsList = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.rightsList)

        related_identifiers = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)

        description = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.descriptions)

        dates = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.dates.date)

        contributors = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)

        creators = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.creators)

        geolocations = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.geoLocations)

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
