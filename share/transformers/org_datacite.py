import logging

from share.transform.chain import ctx, links as tools, ChainTransformer
from share.transform.chain.parsers import Parser
from share.transform.chain.utils import force_text


logger = logging.getLogger(__name__)

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
NOT_PEOPLE_TYPES = (
    'Distributor',
    'HostingInstitution',
    'RegistrationAgency',
    'RegistrationAuthority',
    'ResearchGroup'
)
# Other ambiguous types
#   'DataCollector',
#   'DataManager',
#   'Producer',
#   'RightsHolder',
#   'Sponsor',
#   'Other'


def try_contributor_type(value, target_list_types):
    try:
        contrib_type_item = value['@contributorType']
        if contrib_type_item in target_list_types:
            return value
        return None
    except KeyError:
        return None


def get_contributors(options, contrib_type):
    """
    Returns list of contributors names based on their type.
    """
    contribs = []
    for value in options:
        val = try_contributor_type(value, contrib_type)
        if val:
            contribs.append(val)
    return contribs


def get_agent_type(agent, person=False):
    """
    Returns agent type based on contributor type.
    """
    is_not_person = try_contributor_type(agent, NOT_PEOPLE_TYPES)
    is_person = try_contributor_type(agent, PEOPLE_TYPES)
    try:
        agent_name = agent.creatorName
    except KeyError:
        agent_name = agent.contributorName

    if person and is_person:
        return agent_name
    elif not person and is_not_person:
        return agent_name
    # break OneOf option
    raise KeyError()


RELATION_MAP = {
    'IsCitedBy': 'Cites',
    'Cites': 'Cites',
    'IsSupplementedBy': 'IsSupplementTo',
    'IsSupplementTo': 'IsSupplementTo',
    'IsContinuedBy': 'Extends',
    'Continues': 'Extends',
    'IsNewVersionOf': '',
    'IsPreviousVersionOf': '',
    'References': 'References',
    'IsReferencedBy': 'References',
    'IsPartOf': 'IsPartOf',
    'HasPart': 'IsPartOf',
    'IsDocumentedBy': 'Documents',
    'Documents': 'Documents',
    'IsCompiledBy': 'Compiles',
    'Compiles': 'Compiles',
    'IsVariantFormOf': '',
    'IsOriginalFormOf': '',
    'IsReviewedBy': 'Reviews',
    'Reviews': 'Reviews',
    'IsDerivedFrom': 'IsDerivedFrom',
    'IsSourceOf': 'IsDerivedFrom',
    'IsMetadataFor': '',
    'HasMetadata': '',
}

INVERSE_RELATIONS = (
    'IsCitedBy',
    'IsSupplementedBy',
    'IsContinuedBy',
    'IsNewVersionOf',
    'IsReferencedBy',
    'IsPartOf',
    'IsDocumentedBy',
    'IsCompiledBy',
    'IsVariantFormOf',
    'IsReviewedBy',
    'IsDerivedFrom',
    'IsMetadataFor'
)

RELATIONS = (
    'Cites',
    'IsSupplementTo',
    'Continues',
    'References',
    'IsPreviousVersionOf',
    'HasPart',
    'Documents',
    'Compiles',
    'IsOriginalFormOf',
    'Reviews',
    'IsSourceOf',
    'HasMetadata',
)


def get_related_works(options, inverse):
    results = []
    for option in options:
        if not option.get('#text') or option['#text'].lower() == 'null':
            continue

        if not option.get('@preprocessed'):
            option['@preprocessed'] = True
            option['#text'] = {
                'PMID': 'http://www.ncbi.nlm.nih.gov/pubmed/{}'
            }.get(option.get('@relatedIdentifierType'), '{}').format(option['#text'])

        relation = option['@relationType']
        if inverse and relation in INVERSE_RELATIONS:
            results.append(option)
        elif not inverse and relation in RELATIONS:
            results.append(option)
    return results


def get_relation_type(relation_type):
    normalized_relation = RELATION_MAP[relation_type]
    return normalized_relation or 'WorkRelation'


class AgentIdentifier(Parser):

    uri = ctx


class AffiliatedAgent(Parser):
    schema = tools.GuessAgentType(ctx, default='organization')

    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AffiliatedAgent, ctx)


class ContributorAgent(Parser):
    schema = tools.OneOf(
        tools.GuessAgentType(
            tools.RunPython(
                get_agent_type,
                ctx,
                person=False
            ),
            default='organization'
        ),
        tools.GuessAgentType(
            tools.OneOf(
                ctx.creatorName,
                ctx.contributorName
            )
        )
    )

    name = tools.OneOf(ctx.creatorName, ctx.contributorName)
    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Try(
            tools.IRI(
                tools.RunPython(
                    force_text,
                    ctx.nameIdentifier
                )
            ),
            exceptions=(ValueError,)
        )
    )
    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), tools.Concat(tools.Try(
        tools.Filter(lambda x: bool(x), tools.RunPython(force_text, ctx.affiliation))
    )))

    class Extra:
        name_identifier = tools.Try(ctx.nameIdentifier)
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])

        contributor_type = tools.Try(ctx.contributorType)

        # v.4 new givenName and familyName properties
        given_name = tools.OneOf(
            ctx.creatorName['@givenName'],
            ctx.contributorName['@givenName'],
            tools.Static(None)
        )
        family_name = tools.OneOf(
            ctx.creatorName['@familyName'],
            ctx.contributorName['@familyName'],
            tools.Static(None)
        )


class FunderAgent(Parser):
    schema = tools.GuessAgentType(
        tools.OneOf(ctx.funderName, ctx.contributorName),
        default='organization'
    )

    name = tools.OneOf(ctx.funderName, ctx.contributorName)

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Try(
            tools.IRI(
                tools.OneOf(
                    ctx.funderIdentifier,
                    tools.RunPython(
                        force_text,
                        ctx.nameIdentifier
                    ),
                    tools.Static(None)
                )
            ),
            exceptions=(ValueError,)
        )
    )

    class Extra:
        name_identifier = tools.Try(ctx.nameIdentifier)
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])

        funder_identifier = tools.Try(ctx.funderIdentifier)
        funder_identifier_type = tools.Try(ctx.funderIdentifierType)

        contributor_type = tools.Try(ctx.contributorType)


class HostAgent(Parser):
    schema = tools.GuessAgentType(ctx.contributorName, default='organization')

    name = tools.Try(ctx.contributorName)

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Try(
            tools.IRI(
                tools.RunPython(
                    force_text,
                    ctx.nameIdentifier
                )
            ),
            exceptions=(ValueError,)
        )
    )

    class Extra:
        name_identifier = tools.Try(ctx.nameIdentifier)
        name_identifier_scheme = tools.Try(ctx.nameIdentifier['@nameIdentifierScheme'])
        name_identifier_scheme_uri = tools.Try(ctx.nameIdentifier['@schemeURI'])

        contributor_type = tools.Try(ctx.contributorType)


class PublisherAgent(Parser):
    schema = tools.GuessAgentType(ctx, default='organization')

    name = ctx


class ContributorRelation(Parser):
    schema = 'Contributor'

    agent = tools.Delegate(ContributorAgent, ctx)
    cited_as = tools.OneOf(ctx.creatorName, ctx.contributorName)


class CreatorRelation(ContributorRelation):
    schema = 'Creator'

    order_cited = ctx('index')


class HostRelation(Parser):
    schema = 'Host'

    agent = tools.Delegate(HostAgent, ctx)


class PublisherRelation(Parser):
    schema = 'Publisher'

    agent = tools.Delegate(PublisherAgent, ctx)


class Award(Parser):
    name = tools.Try(ctx.awardTitle)
    description = tools.Try(ctx.awardNumber)
    uri = tools.Try(ctx.awardURI)


class ThroughAwards(Parser):
    award = tools.Delegate(Award, ctx)


class FunderRelation(Parser):
    schema = 'Funder'

    agent = tools.Delegate(FunderAgent, ctx)
    awards = tools.Map(tools.Delegate(ThroughAwards), tools.Try(tools.RunPython('get_award', ctx)))

    def get_award(self, obj):
        obj['awardURI']
        return obj


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class WorkIdentifier(Parser):
    uri = tools.DOI(tools.RunPython(
        force_text,
        ctx
    ))

    class Extra:
        identifier_type = tools.Try(ctx['@identifierType'])


class RelatedWorkIdentifier(Parser):
    schema = 'WorkIdentifier'

    uri = tools.IRI(tools.RunPython(
        force_text,
        ctx
    ))

    class Extra:
        related_identifier_type = ctx['@relatedIdentifierType']
        relation_type = tools.Try(ctx['@relationType'])
        related_metadata_scheme = tools.Try(ctx['@relatedMetadataScheme'])
        scheme_URI = tools.Try(ctx['@schemeURI'])
        scheme_type = tools.Try(ctx['@schemeType'])


class RelatedWork(Parser):
    schema = 'CreativeWork'
    identifiers = tools.Map(tools.Delegate(RelatedWorkIdentifier), ctx)


class WorkRelation(Parser):
    schema = tools.RunPython(get_relation_type, ctx['@relationType'])
    related = tools.Delegate(RelatedWork, ctx)


class InverseWorkRelation(Parser):
    schema = tools.RunPython(get_relation_type, ctx['@relationType'])
    subject = tools.Delegate(RelatedWork, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class CreativeWork(Parser):
    '''
    Documentation for Datacite's metadata:
    https://schema.labs.datacite.org/meta/kernel-4.0/doc/DataCite-MetadataKernel_v4.0.pdf
    '''

    def get_schema(self, type):
        return {
            'dataset': 'DataSet',
            'software': 'Software',
            'text/book': 'Book',
            'text/book chapter': 'Book',
            'text/book prospectus': 'Book',
            'text/book series': 'Book',
            'text/conference abstract': 'ConferencePaper',
            'text/conference paper': 'ConferencePaper',
            'text/conference poster': 'Poster',
            'text/dissertation': 'Dissertation',
            'text/edited book': 'Book',
            'text/journal article': 'Article',
            'text/journal issue': 'Article',
            'text/patent': 'Patent',
            'text/report': 'Report',
            'text/supervised student publication': 'Thesis',
            'text/working paper': 'WorkingPaper'

            # 'audiovisual': '',
            # 'collection': '',
            # 'event': '',
            # 'image': '',
            # 'interactiveresource': '',
            # 'model': '',
            # 'physicalobject': '',
            # 'service': '',
            # 'sound': '',
            # 'text15': '',
            # 'workflow': '',
            # 'text/book review': '',
            # 'text/conference program': '',
            # 'text/dictionary entry': '',
            # 'text/disclosure': '',
            # 'text/encyclopedia entry': '',
            # 'text/Funding submission': '',
            # 'text/license': '',
            # 'text/magazine article': '',
            # 'text/manual': '',
            # 'text/newsletter article': '',
            # 'text/newspaper article': '',
            # 'text/online resource': '',
            # 'text/registered copyright': '',
            # 'text/research tool': '',
            # 'text/tenure-promotion': '',
            # 'text/test': '',
            # 'text/trademark': '',
            # 'text/translation': '',
            # 'text/university academic unit': '',
            # 'text/website': '',
        }.get(type.lower()) or 'CreativeWork'

    schema = tools.RunPython(
        'get_schema', tools.Try(
            ctx.record.metadata['oai_datacite'].payload.resource.resourceType['@resourceTypeGeneral'],
            default='CreativeWork'
        )
    )

    title = tools.RunPython(
        force_text,
        tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.titles.title)
    )

    description = tools.Try(
        tools.Join(
            tools.RunPython(
                force_text,
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.descriptions.description)
            )
        )
    )

    rights = tools.Try(
        tools.Join(
            tools.RunPython(
                force_text,
                tools.Concat(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights)
            )
        )
    )

    language = tools.ParseLanguage(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.language))

    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(CreatorRelation),
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.creators.creator))
        ),
        tools.Map(
            tools.Delegate(ContributorRelation),
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor))
        ),
        tools.Map(tools.Delegate(
            PublisherRelation),
            tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.publisher)
        ),
        tools.Map(tools.Delegate(HostRelation), tools.RunPython(
            get_contributors,
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
            ['HostingInstitution']
        )),
        # v.3 Funder is a contributor type
        # v.4 FundingReference replaces funder contributor type
        tools.Map(tools.Delegate(FunderRelation), tools.RunPython(
            get_contributors,
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.contributors.contributor)),
            ['Funder']
        )),
        tools.Map(
            tools.Delegate(FunderRelation),
            tools.Concat(tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.fundingReference))
        )
    )

    # v.4 New, free text, 'subjectScheme' attribute on subject
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Subjects(
            tools.RunPython(
                force_text,
                tools.Concat(
                    tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.subjects.subject),
                )
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
                    force_text,
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

    identifiers = tools.Concat(
        tools.Map(
            tools.Delegate(WorkIdentifier),
            tools.Concat(
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.identifier)
            )
        ),
        tools.Map(
            tools.Delegate(WorkIdentifier),
            tools.Concat(
                tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.alternateIdentifiers.alternateidentifier)
            )
        )
    )

    related_works = tools.Concat(
        tools.Map(
            tools.Delegate(WorkRelation),
            tools.RunPython(
                get_related_works,
                tools.Concat(
                    tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)
                ),
                False
            )
        ),
        tools.Map(
            tools.Delegate(InverseWorkRelation),
            tools.RunPython(
                get_related_works,
                tools.Concat(
                    tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.relatedIdentifiers.relatedIdentifier)
                ),
                True
            )
        )
    )

    date_updated = tools.ParseDate(tools.Try(ctx.record.header.datestamp))
    date_published = tools.ParseDate(tools.Try(tools.RunPython('get_date_type', tools.Concat(ctx.record.metadata['oai_datacite'].payload.resource.dates.date), 'Issued')))
    free_to_read_type = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.rightsList.rights['@rightsURI'])
    free_to_read_date = tools.ParseDate(tools.Try(tools.RunPython('get_date_type', tools.Concat(ctx.record.metadata['oai_datacite'].payload.resource.dates.date), 'Available')))

    is_deleted = tools.RunPython('check_status', tools.Try(ctx.record.header['@status']))

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        status = tools.Try(ctx.record.header['@status'])

        datestamp = tools.ParseDate(ctx.record.header.datestamp)

        set_spec = tools.Try(ctx.record.header.setSpec)

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

        # v.4 new property geoLocationPolygon, in addition to geoLocationPoint and geoLocationBox
        geolocations = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.geoLocations)

        funding_reference = tools.Try(ctx.record.metadata['oai_datacite'].payload.resource.fundingReference)

    def check_status(self, status):
        if status == 'deleted':
            return True
        return False

    def get_date_type(self, date_obj, date_type):
        date = None
        for obj in date_obj:
            if obj['@dateType'] == date_type:
                date = obj['#text']
        if date and date != '0000':
            return date
        # raise KeyError to break TryLink
        raise KeyError()


class DataciteTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
