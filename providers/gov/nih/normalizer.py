from share.normalize import *
from share.normalize.utils import format_address


PROJECT_BASE_URL = 'https://projectreporter.nih.gov/project_info_description.cfm?aid={}'
FOA_BASE_URL = 'https://grants.nih.gov/grants/guide/pa-files/{}.html'


def filter_nil(obj):
        if isinstance(obj, dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj


class WorkIdentifier(Parser):
    uri = RunPython('format_nih_url', ctx)

    def format_nih_url(self, id):
        return PROJECT_BASE_URL.format(id)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class AwardeeAgent(Parser):
    schema = GuessAgentType(
        ctx.ORG_NAME,
        default='organization'
    )

    name = ctx.ORG_NAME
    location = RunPython('format_org_address', ctx)

    class Extra:
        awardee_organization_duns = ctx.ORG_DUNS
        awardee_organization_fips = ctx.ORG_FIPS
        awardee_organization_dept = ctx.ORG_DEPT
        awardee_organization_district = ctx.ORG_DISTRICT
        awardee_organization_city = ctx.ORG_CITY
        awardee_organization_state = ctx.ORG_STATE
        awardee_organization_zipcode = ctx.ORG_ZIPCODE
        awardee_organization_country = ctx.ORG_COUNTRY

    def format_org_address(self, doc):
        return format_address(
            self,
            city=doc.get('ORG_CITY'),
            state_or_province=doc.get('ORG_STATE'),
            postal_code=doc.get('ORG_ZIPCODE'),
            country=doc.get('ORG_COUNTRY')
        )


class AgentRelation(Parser):
    related = Delegate(AwardeeAgent, ctx)


class FunderAgent(Parser):
    schema = GuessAgentType(
        ctx.IC_NAME,
        default='organization'
    )

    # The full name of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    name = ctx.IC_NAME
    related_agents = Map(Delegate(AgentRelation), RunPython('get_organization_ctx', ctx))

    class Extra:
        # The organizational code of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
        acronym = RunPython(filter_nil, ctx.ADMINISTERING_IC)
        funding_ics = ctx.FUNDING_ICs
        funding_mechanism = ctx.FUNDING_MECHANISM

    def get_organization_ctx(self, ctx):
        org_ctx = {
            'ORG_NAME': ctx['ORG_NAME'],
            'ORG_FIPS': ctx['ORG_FIPS'],
            'ORG_DEPT': ctx['ORG_DEPT'],
            'ORG_DUNS': ctx['ORG_DUNS'],
            'ORG_DISTRICT': ctx['ORG_DISTRICT'],
            'ORG_CITY': ctx['ORG_CITY'],
            'ORG_STATE': ctx['ORG_STATE'],
            'ORG_ZIPCODE': ctx['ORG_ZIPCODE'],
            'ORG_COUNTRY': ctx['ORG_COUNTRY']
        }
        return org_ctx


class Award(Parser):
    name = ctx.PROJECT_TITLE
    # The amount of the award provided by the funding NIH Institute(s) or Center(s)
    description = RunPython('get_award_amount', ctx.FUNDING_ICs)
    uri = RunPython('format_foa_url', ctx.FOA_NUMBER)

    class Extra:
        awardee_name = ctx.ORG_NAME
        awardee_organization_duns = ctx.ORG_DUNS
        awardee_organization_fips = ctx.ORG_FIPS
        awardee_organization_dept = ctx.ORG_DEPT
        awardee_organization_district = ctx.ORG_DISTRICT

        arra_funded = ctx.ARRA_FUNDED
        award_notice_date = ctx.AWARD_NOTICE_DATE

        support_year = ctx.SUPPORT_YEAR
        foa_number = ctx.FOA_NUMBER

    def get_award_amount(self, award_info):
        if not award_info or (isinstance(award_info, dict) and award_info.get('@http://www.w3.org/2001/XMLSchema-instance:nil')):
            return None
        return award_info.split(':')[1].replace('\\', '')

    def format_foa_url(self, foa_number):
        return FOA_BASE_URL.format(foa_number)


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class FunderRelation(Parser):
    schema = 'Funder'

    agent = Delegate(FunderAgent, ctx)
    awards = Map(Delegate(ThroughAwards), ctx)


class POAgent(Parser):
    schema = 'Person'

    name = ctx


class PIAgent(Parser):
    schema = 'Person'

    name = ctx.PI_NAME

    class Extra:
        pi_id = ctx.PI_ID


class PIRelation(Parser):
    schema = 'PrincipalInvestigator'

    agent = Delegate(PIAgent, ctx)
    cited_as = ctx.PI_NAME


class PORelation(Parser):
    schema = 'Contributor'

    agent = Delegate(POAgent, ctx)
    cited_as = ctx


class Project(Parser):
    title = ctx.row.PROJECT_TITLE
    related_agents = Concat(
        Map(Delegate(PIRelation), Try(ctx.row.PIS.PI)),
        Map(Delegate(PORelation), RunPython(filter_nil, ctx.row.PROGRAM_OFFICER_NAME)),
        Map(Delegate(FunderRelation), ctx.row),
    )

    identifiers = Map(
        Delegate(WorkIdentifier), ctx.row.APPLICATION_ID
    )

    subjects = Map(
        Delegate(ThroughSubjects),
        Subjects(Try(ctx.row.PROJECT_TERMSX.TERM))
    )

    tags = Map(
        Delegate(ThroughTags),
        Try(ctx.row.PROJECT_TERMSX.TERM)
    )

    class Extra:
        activity = ctx.row.ACTIVITY
        application_id = ctx.row.APPLICATION_ID
        budget_start = ctx.row.BUDGET_START
        budget_end = ctx.row.BUDGET_END
        cfda_code = ctx.row.CFDA_CODE
        core_project_number = ctx.row.CORE_PROJECT_NUM
        ed_inst_type = ctx.row.ED_INST_TYPE
        fiscal_year = ctx.row.FY
        full_project_number = ctx.row.FULL_PROJECT_NUM
        nih_spending_cats = ctx.row.NIH_SPENDING_CATS
        phr = ctx.row.PHR
        project_start = ctx.row.PROJECT_START
        project_end = ctx.row.PROJECT_END
        serial_number = ctx.row.SERIAL_NUMBER
        study_section = ctx.row.STUDY_SECTION
        study_section_name = ctx.row.STUDY_SECTION_NAME
        subproject_id = ctx.row.SUBPROJECT_ID
        suffix = ctx.row.SUFFIX
        total_cost = ctx.row.TOTAL_COST
        total_cost_subproject = ctx.row.TOTAL_COST_SUB_PROJECT

    def parse_awards(self, award_info):
        return [award for award in award_info.split(';')]

    def maybe_org(self, obj):
        if isinstance(obj.get('ORG_NAME'), dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj
