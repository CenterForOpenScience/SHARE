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
        awardee_organization_duns = RunPython(filter_nil, ctx.ORG_DUNS)
        awardee_organization_fips = RunPython(filter_nil, ctx.ORG_FIPS)
        awardee_organization_dept = RunPython(filter_nil, ctx.ORG_DEPT)
        awardee_organization_district = RunPython(filter_nil, ctx.ORG_DISTRICT)
        awardee_organization_city = RunPython(filter_nil, ctx.ORG_CITY)
        awardee_organization_state = RunPython(filter_nil, ctx.ORG_STATE)
        awardee_organization_zipcode = RunPython(filter_nil, ctx.ORG_ZIPCODE)
        awardee_organization_country = RunPython(filter_nil, ctx.ORG_COUNTRY)

    def format_org_address(self, doc):
        org_city = doc.get('ORG_CITY') if not doc.get('ORG_CITY').get('@http://www.w3.org/2001/XMLSchema-instance:nil') else ''
        org_state = doc.get('ORG_STATE') if not doc.get('ORG_STATE').get('@http://www.w3.org/2001/XMLSchema-instance:nil') else ''
        org_zipcode = doc.get('ORG_ZIPCODE') if not doc.get('ORG_ZIPCODE').get('@http://www.w3.org/2001/XMLSchema-instance:nil') else ''
        org_country = doc.get('ORG_COUNTRY') if not doc.get('ORG_COUNTRY').get('@http://www.w3.org/2001/XMLSchema-instance:nil') else ''
        if not org_city and not org_state and not org_zipcode and not org_country:
            return None
        return format_address(
            self,
            city=org_city,
            state_or_province=org_state,
            postal_code=org_zipcode,
            country=org_country
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
    related_agents = Map(
        Delegate(AgentRelation),
        RunPython('get_organization_ctx', RunPython(filter_nil, ctx))
    )

    class Extra:
        # The organizational code of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
        acronym = RunPython(filter_nil, ctx.ADMINISTERING_IC)
        funding_ics = RunPython(filter_nil, ctx.FUNDING_ICs)
        funding_mechanism = RunPython(filter_nil, ctx.FUNDING_MECHANISM)

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
    description = RunPython('get_award_amount', RunPython(filter_nil, ctx.FUNDING_ICs))
    uri = RunPython('format_foa_url', RunPython(filter_nil, ctx.FOA_NUMBER))

    class Extra:
        awardee_name = RunPython(filter_nil, ctx.ORG_NAME)
        awardee_organization_duns = RunPython(filter_nil, ctx.ORG_DUNS)
        awardee_organization_fips = RunPython(filter_nil, ctx.ORG_FIPS)
        awardee_organization_dept = RunPython(filter_nil, ctx.ORG_DEPT)
        awardee_organization_district = RunPython(filter_nil, ctx.ORG_DISTRICT)

        arra_funded = RunPython(filter_nil, ctx.ARRA_FUNDED)
        award_notice_date = RunPython(filter_nil, ctx.AWARD_NOTICE_DATE)

        support_year = RunPython(filter_nil, ctx.SUPPORT_YEAR)
        foa_number = RunPython(filter_nil, ctx.FOA_NUMBER)

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
        pi_id = RunPython(filter_nil, ctx.PI_ID)


class PIRelation(Parser):
    schema = 'PrincipalInvestigator'

    agent = Delegate(PIAgent, ctx)
    cited_as = ctx.PI_NAME


class PORelation(Parser):
    schema = 'Contributor'

    agent = Delegate(POAgent, ctx)
    cited_as = ctx


class Project(Parser):
    title = RunPython(filter_nil, ctx.row.PROJECT_TITLE)
    related_agents = Concat(
        Map(Delegate(PIRelation), RunPython(filter_nil, Try(ctx.row.PIS.PI))),
        Map(Delegate(PORelation), RunPython(filter_nil, ctx.row.PROGRAM_OFFICER_NAME)),
        Map(Delegate(FunderRelation), RunPython(filter_nil, ctx.row)),
    )

    identifiers = Map(
        Delegate(WorkIdentifier), RunPython(filter_nil, ctx.row.APPLICATION_ID)
    )

    subjects = Map(
        Delegate(ThroughSubjects),
        Subjects(RunPython(filter_nil, Try(ctx.row.PROJECT_TERMSX.TERM)))
    )

    tags = Map(
        Delegate(ThroughTags),
        RunPython(filter_nil, Try(ctx.row.PROJECT_TERMSX.TERM))
    )

    class Extra:
        activity = RunPython(filter_nil, ctx.row.ACTIVITY)
        application_id = RunPython(filter_nil, ctx.row.APPLICATION_ID)
        budget_start = RunPython(filter_nil, ctx.row.BUDGET_START)
        budget_end = RunPython(filter_nil, ctx.row.BUDGET_END)
        cfda_code = RunPython(filter_nil, ctx.row.CFDA_CODE)
        core_project_number = RunPython(filter_nil, ctx.row.CORE_PROJECT_NUM)
        ed_inst_type = RunPython(filter_nil, ctx.row.ED_INST_TYPE)
        fiscal_year = RunPython(filter_nil, ctx.row.FY)
        full_project_number = RunPython(filter_nil, ctx.row.FULL_PROJECT_NUM)
        nih_spending_cats = RunPython(filter_nil, ctx.row.NIH_SPENDING_CATS)
        phr = RunPython(filter_nil, ctx.row.PHR)
        project_start = RunPython(filter_nil, ctx.row.PROJECT_START)
        project_end = RunPython(filter_nil, ctx.row.PROJECT_END)
        serial_number = RunPython(filter_nil, ctx.row.SERIAL_NUMBER)
        study_section = RunPython(filter_nil, ctx.row.STUDY_SECTION)
        study_section_name = RunPython(filter_nil, ctx.row.STUDY_SECTION_NAME)
        subproject_id = RunPython(filter_nil, ctx.row.SUBPROJECT_ID)
        suffix = RunPython(filter_nil, ctx.row.SUFFIX)
        total_cost = RunPython(filter_nil, ctx.row.TOTAL_COST)
        total_cost_subproject = RunPython(filter_nil, ctx.row.TOTAL_COST_SUB_PROJECT)

    def parse_awards(self, award_info):
        return [award for award in award_info.split(';')]

    def maybe_org(self, obj):
        if isinstance(obj.get('ORG_NAME'), dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj
