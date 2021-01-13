from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.exceptions import InvalidIRI
from share.transform.chain.parsers import Parser
from share.transform.chain.utils import format_address


def format_url(award_id):
    return 'https://www.nsf.gov/awardsearch/showAward?AWD_ID={}'.format(award_id)


def format_org_address(ctx):
    awardee_address = ctx.get('awardeeAddress', '')
    awardee_city = ctx.get('awardeeCity', '')
    awardee_state_code = ctx.get('awardeeStateCode', '')
    awardee_country_code = ctx.get('awardeeCountryCode', '')
    awardee_zip_code = ctx.get('awardeeZipCode', '')

    if not any((awardee_address, awardee_city, awardee_state_code, awardee_zip_code, awardee_country_code)):
        return None

    return format_address(
        address1=awardee_address,
        city=awardee_city,
        state_or_province=awardee_state_code,
        postal_code=awardee_zip_code,
        country=awardee_country_code
    )


class WorkIdentifier(Parser):
    uri = tools.RunPython(format_url, ctx.id)


class FunderAgent(Parser):
    schema = tools.GuessAgentType(
        ctx.agency,
        default='organization'
    )

    name = ctx.agency


class Award(Parser):
    name = ctx.title
    description = ctx.fundsObligatedAmt
    award_amount = tools.Int(ctx.fundsObligatedAmt)
    date = tools.ParseDate(ctx.date)
    uri = tools.RunPython(format_url, ctx.id)

    class Extra:
        funds_obligated_amt = ctx.fundsObligatedAmt
        award_id = ctx.id
        transaction_type = ctx.transType
        estimated_total_amt = tools.Try(ctx.estimatedTotalAmt)
        catalog_of_federal_domestic_assistance_number = tools.Try(ctx.cfdaNumber)

        date = ctx.date
        date_start = tools.Try(ctx.startDate)
        date_expiration = tools.Try(ctx.expDate)

        awardee = tools.Try(ctx.awardee)
        awardee_address = tools.Try(ctx.awardeeAddress)
        awardee_name = ctx.awardeeName
        awardee_city = tools.Try(ctx.awardeeCity)
        awardee_county = tools.Try(ctx.awardeeCounty)
        awardee_state_code = tools.Try(ctx.awardeeStateCode)
        awardee_country_code = tools.Try(ctx.awardeeCountryCode)
        awardee_district_code = tools.Try(ctx.awardeeDistrictCode)
        awardee_zip_code = tools.Try(ctx.awardeeZipCode)


class ThroughAwards(Parser):
    award = tools.Delegate(Award, ctx)


class FunderRelation(Parser):
    schema = 'Funder'

    agent = tools.Delegate(FunderAgent, ctx)
    awards = tools.Map(tools.Delegate(ThroughAwards), ctx)


class AffiliatedAgent(Parser):
    schema = tools.GuessAgentType(
        ctx.awardeeName,
        default='organization'
    )

    name = ctx.awardeeName
    location = tools.RunPython(format_org_address, ctx)

    class Extra:
        awardee = tools.Try(ctx.awardee)
        awardee_address = tools.Try(ctx.awardeeAddress)
        awardee_name = ctx.awardeeName
        awardee_city = tools.Try(ctx.awardeeCity)
        awardee_county = tools.Try(ctx.awardeeCounty)
        awardee_state_code = tools.Try(ctx.awardeeStateCode)
        awardee_country_code = tools.Try(ctx.awardeeCountryCode)
        awardee_district_code = tools.Try(ctx.awardeeDistrictCode)
        awardee_zip_code = tools.Try(ctx.awardeeZipCode)


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AffiliatedAgent, ctx)


class AgentIdentifier(Parser):
    uri = ctx


class POContributorAgent(Parser):
    schema = 'Person'

    name = ctx.poName

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Try(
            tools.IRI(ctx.poEmail),
            exceptions=(InvalidIRI,)
        )
    )

    related_agents = tools.Map(
        tools.Delegate(IsAffiliatedWith),
        tools.Filter(lambda x: 'awardeeName' in x, ctx)
    )

    class Extra:
        po_name = tools.Try(ctx.poName)
        po_email = tools.Try(ctx.poEmail)


class POContributorRelation(Parser):
    schema = 'Contributor'

    agent = tools.Delegate(POContributorAgent, ctx)
    cited_as = ctx.poName


class PIContributorAgent(Parser):
    schema = 'Person'

    family_name = ctx.piLastName
    given_name = ctx.piFirstName
    additional_name = tools.Try(ctx.piMiddeInitial)

    related_agents = tools.Map(
        tools.Delegate(IsAffiliatedWith),
        tools.Filter(lambda x: 'awardeeName' in x, ctx)
    )

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Try(
            tools.IRI(ctx.piEmail),
            exceptions=(InvalidIRI,)
        )
    )

    class Extra:
        pi_last_name = ctx.piLastName
        pi_first_name = ctx.piFirstName
        pi_middle_initial = tools.Try(ctx.piMiddeInitial)
        pi_email = tools.Try(ctx.piEmail)


class PIContributorRelation(Parser):
    schema = 'PrincipalInvestigatorContact'

    agent = tools.Delegate(PIContributorAgent, ctx)
    cited_as = tools.Join(
        tools.Concat(ctx.piFirstName, ctx.piLastName),
        joiner=' '
    )


class AgentWorkRelation(Parser):
    agent = tools.Delegate(AffiliatedAgent, ctx)


class CreativeWork(Parser):
    # https://www.research.gov/common/webapi/awardapisearch-v1.htm#request-parameters

    title = ctx.title
    description = ctx.abstractText

    identifiers = tools.Map(tools.Delegate(WorkIdentifier), ctx)

    related_agents = tools.Concat(
        tools.Map(tools.Delegate(FunderRelation), ctx),
        tools.Map(tools.Delegate(PIContributorRelation), ctx),
        tools.Map(
            tools.Delegate(POContributorRelation),
            tools.Filter(lambda x: x.get('poName') is not None, ctx)
        ),
        tools.Map(
            tools.Delegate(AgentWorkRelation),
            tools.Filter(lambda x: x.get('awardeeName') is not None, ctx)
        )
    )

    date_updated = tools.ParseDate(ctx.date)

    class Extra:
        catalog_of_federal_domestic_assistance_number = tools.Try(ctx.cfdaNumber)
        estimated_total_amt = tools.Try(ctx.estimatedTotalAmt)
        fund_program_name = tools.Try(ctx.fundProgramName)
        has_project_outcomes_report = tools.Try(ctx.projectOutComesReport)
        primary_program = tools.Try(ctx.primaryProgram)
        public_access_mandate = tools.Try(ctx.publicAccessMandate)
        transaction_type = tools.Try(ctx.transType)

        co_pi_name = tools.Try(ctx.coPDPI)  # irregular field (ex. [First Last ~<numbers>, ...])
        proj_dir_pi_name = tools.Try(ctx.pdPIName)

        duns_number = tools.Try(ctx.dunsNumber)
        parent_duns_number = tools.Try(ctx.parentDunsNumber)

        fund_agency_code = tools.Try(ctx.fundAgencyCode)
        award_agency_code = tools.Try(ctx.awardAgencyCode)

        publication_research = tools.Try(ctx.publicationResearch)
        publication_conference = tools.Try(ctx.publicationConference)

        po_name = tools.Try(ctx.poName)
        po_email = tools.Try(ctx.poEmail)

        date = ctx.date
        date_start = tools.Try(ctx.startDate)
        date_expiration = tools.Try(ctx.expDate)

        pi_last_name = ctx.piLastName
        pi_first_name = ctx.piFirstName
        pi_middle_initial = tools.Try(ctx.piMiddeInitial)
        pi_email = tools.Try(ctx.piEmail)

        awardee = tools.Try(ctx.awardee)
        awardee_address = tools.Try(ctx.awardeeAddress)
        awardee_city = tools.Try(ctx.awardeeCity)
        awardee_country_code = tools.Try(ctx.awardeeCountryCode)
        awardee_county = tools.Try(ctx.awardeeCounty)
        awardee_district_code = tools.Try(ctx.awardeeDistrictCode)
        awardee_name = tools.Try(ctx.awardeeName)
        awardee_state_code = tools.Try(ctx.awardeeStateCode)
        awardee_zip_code = tools.Try(ctx.awardeeZipCode)

        performance_address = tools.Try(ctx.perfAddress)
        performance_city = tools.Try(ctx.perfCity)
        performance_country_code = tools.Try(ctx.perfCountryCode)
        performance_county = tools.Try(ctx.perfCounty)
        performance_district_code = tools.Try(ctx.perfDistrictCode)
        performance_location = tools.Try(ctx.perfLocation)
        performance_state_code = tools.Try(ctx.perfStateCode)
        performance_zip_code = tools.Try(ctx.perfZipCode)


class NSFTransformer(ChainTransformer):
    VERSION = 2
    root_parser = CreativeWork
