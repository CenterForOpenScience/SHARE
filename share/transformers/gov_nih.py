import re

from share.transform.chain import *
import share.transform.chain.links as tools
from share.transform.chain.utils import format_address


PROJECT_BASE_URL = 'https://projectreporter.nih.gov/project_info_description.cfm?aid={}'
FOA_BASE_URL = 'https://grants.nih.gov/grants/guide/pa-files/{}.html'


def filter_nil(obj):
    if isinstance(obj, dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
        return None
    return obj


def format_org_address(doc):
    org_city = doc.get('ORG_CITY', '')
    org_state = doc.get('ORG_STATE', '')
    org_zipcode = doc.get('ORG_ZIPCODE', '')
    org_country = doc.get('ORG_COUNTRY', '')
    if not any((org_city, org_state, org_zipcode, org_country)):
        return None
    return format_address(
        city=org_city,
        state_or_province=org_state,
        postal_code=org_zipcode,
        country=org_country
    )


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
    location = RunPython(format_org_address, ctx)

    class Extra:
        awardee_organization_duns = ctx.ORG_DUNS
        awardee_organization_fips = ctx.ORG_FIPS
        awardee_organization_dept = ctx.ORG_DEPT
        awardee_organization_district = ctx.ORG_DISTRICT
        awardee_organization_city = ctx.ORG_CITY
        awardee_organization_state = ctx.ORG_STATE
        awardee_organization_zipcode = ctx.ORG_ZIPCODE
        awardee_organization_country = ctx.ORG_COUNTRY


class AgentWorkRelation(Parser):
    agent = Delegate(AwardeeAgent, ctx)


class FunderAgent(Parser):
    schema = GuessAgentType(
        ctx.IC_NAME,
        default='organization'
    )

    # The full name of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    name = ctx.IC_NAME

    # class Extra:
    #     The organizational code of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    #     acronym = RunPython(filter_nil, ctx.ADMINISTERING_IC)
    #     funding_ics = RunPython(filter_nil, ctx.FUNDING_ICs)
    #     funding_mechanism = RunPython(filter_nil, ctx.FUNDING_MECHANISM)


class Award(Parser):
    name = ctx.PROJECT_TITLE
    # The amount of the award provided by the funding NIH Institute(s) or Center(s)
    description = RunPython(filter_nil, ctx.FUNDING_ICs)
    award_amount = Int(RunPython(filter_nil, ctx.TOTAL_COST))
    date = Try(
        ParseDate(RunPython(filter_nil, ctx.BUDGET_START)),
        exceptions=(InvalidDate,),
    )
    uri = RunPython('format_nih_url', RunPython(filter_nil, ctx.APPLICATION_ID))

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

    def format_nih_url(self, id):
        return PROJECT_BASE_URL.format(id)

    # FOA's are NOT unique per award. AFAIK only the projects, themselves, are
    # def format_foa_url(self, foa_number):
    #     return FOA_BASE_URL.format(foa_number)


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class FunderRelation(Parser):
    schema = 'Funder'

    agent = Delegate(FunderAgent, ctx)
    awards = Map(Delegate(ThroughAwards), ctx)


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AwardeeAgent, ctx)


class POAgent(Parser):
    schema = 'Person'

    name = ctx


class PIAgent(Parser):
    schema = 'Person'

    name = ctx.PI_NAME
    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), ctx['org_ctx'])

    class Extra:
        pi_id = RunPython(filter_nil, ctx.PI_ID)


class PIContactAgent(Parser):
    schema = 'Person'

    name = ctx.PI_NAME
    related_agents = tools.Concat(
        tools.Map(tools.Delegate(IsAffiliatedWith), ctx['org_ctx']),
    )

    class Extra:
        pi_id = RunPython(filter_nil, ctx.PI_ID)


class PIRelation(Parser):
    schema = 'PrincipalInvestigator'

    agent = Delegate(PIAgent, ctx)
    cited_as = ctx.PI_NAME


class PIContactRelation(Parser):
    schema = 'PrincipalInvestigatorContact'

    agent = Delegate(PIContactAgent, ctx)
    cited_as = ctx.PI_NAME


class PORelation(Parser):
    schema = 'Contributor'

    agent = Delegate(POAgent, ctx)
    cited_as = ctx


class Project(Parser):
    title = RunPython(filter_nil, ctx.row.PROJECT_TITLE)
    related_agents = Concat(
        Map(
            Delegate(PIRelation),
            RunPython(
                'get_pi',
                RunPython(filter_nil, Try(ctx.row)),
                primary=False,
            )
        ),
        Map(
            Delegate(PIContactRelation),
            RunPython(
                'get_pi',
                RunPython(filter_nil, Try(ctx.row)),
            )
        ),
        Map(Delegate(PORelation), RunPython(filter_nil, ctx.row.PROGRAM_OFFICER_NAME)),
        Map(Delegate(AgentWorkRelation), RunPython('get_organization_ctx', RunPython(filter_nil, ctx.row))),
        Map(Delegate(FunderRelation), Filter(lambda x: isinstance(x['IC_NAME'], str) or x['IC_NAME'].get('@http://www.w3.org/2001/XMLSchema-instance:nil') != 'true', ctx.row)),
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
        RunPython(filter_nil, Try(ctx.row.PROJECT_TERMSX.TERM)),
        RunPython(filter_nil, Try(ctx.row.ORG_DEPT))
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

    def get_organization_ctx(self, ctx):
        org_ctx = {
            'ORG_NAME': filter_nil(ctx['ORG_NAME']),
            'ORG_FIPS': filter_nil(ctx['ORG_FIPS']),
            'ORG_DEPT': filter_nil(ctx['ORG_DEPT']),
            'ORG_DUNS': filter_nil(ctx['ORG_DUNS']),
            'ORG_DISTRICT': filter_nil(ctx['ORG_DISTRICT']),
            'ORG_CITY': filter_nil(ctx['ORG_CITY']),
            'ORG_STATE': filter_nil(ctx['ORG_STATE']),
            'ORG_ZIPCODE': filter_nil(ctx['ORG_ZIPCODE']),
            'ORG_COUNTRY': filter_nil(ctx['ORG_COUNTRY'])
        }
        return org_ctx

    def get_pi(self, ctx, primary=True):
        '''
            <PI>
                <PI_NAME>VIDAL, MARC  (contact)</PI_NAME>
                <PI_ID>2094159 (contact)</PI_ID>
            </PI>
        '''
        pi_list = ctx['PIS']['PI'] if isinstance(ctx['PIS']['PI'], list) else [ctx['PIS']['PI']]
        org_ctx = self.get_organization_ctx(ctx)
        # if only one primary contact is assumed
        if len(pi_list) <= 1:
            if not primary:
                return None
            pi_list[0]['org_ctx'] = org_ctx
            return pi_list
        # more than one, get the primary
        if primary:
            try:
                pi = next(x for x in pi_list if '(contact)' in x['PI_NAME'])
            except StopIteration:
                return []

            return {
                'PI_NAME': re.sub(r'(\(contact\))', '', pi['PI_NAME']).strip(),
                'PI_ID': re.sub(r'(\(contact\))', '', pi['PI_ID']).strip(),
                'org_ctx': org_ctx
            }
        # more than one, get the non-primary
        non_primary_pi = []
        for pi in pi_list:
            if '(contact)' not in pi['PI_NAME']:
                pi['org_ctx'] = org_ctx
                non_primary_pi.append(pi)
        return non_primary_pi


class NIHTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Project
