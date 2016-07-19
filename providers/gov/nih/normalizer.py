from share.normalize import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.PI_NAME
    person = Delegate(Person, ctx.PI_NAME)

    class Extra:
        pi_id = ctx.PI_ID


class ProgramOfficer(Parser):
    schema = 'Contributor'

    order_cited = ctx('index')
    cited_name = ctx
    person = Delegate(Person, ctx)


class Link(Parser):
    url = ctx
    type = Static('provider')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Funder(Parser):
    # The full name of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    name = ctx.IC_NAME

    # The organizational code of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    community_identifier = ctx.ADMINISTERING_IC

    class Extra:
        funding_ics = ctx.FUNDING_ICs
        funding_mechanism = ctx.FUNDING_MECHANISM


class ThroughAwardEntities(Parser):
    entity = Delegate(Funder, ctx)


class Award(Parser):

    def get_award_amount(self, award_info):
        if award_info:
            return award_info.split(':')[1].replace('\\', '')
        return None

    # The amount of the award provided by the funding NIH Institute(s) or Center(s)
    description = RunPython('get_award_amount', ctx.FUNDING_ICs)
    entities = Map(Delegate(ThroughAwardEntities), ctx)

    class Extra:
        arra_funded = ctx.ARRA_FUNDED
        award_notice_date = ctx.AWARD_NOTICE_DATE


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class CreativeWork(Parser):

    PROJECT_BASE_URL = 'https://projectreporter.nih.gov/project_info_description.cfm?aid={}'
    FOA_BASE_URL = 'https://grants.nih.gov/grants/guide/pa-files/{}.html'

    def format_nih_url(self, id):
        return self.PROJECT_BASE_URL.format(id)

    def format_foa_url(self, foa_number):
        return self.FOA_BASE_URL.format(foa_number)

    def parse_awards(self, award_info):
        return [award for award in award_info.split(';')]

    title = ctx.row.PROJECT_TITLE
    contributors = Concat(
        Map(Delegate(Contributor), ctx.row.PIS.PI),
        Map(Delegate(ProgramOfficer), ctx.row.PROGRAM_OFFICER_NAME)
    )
    links = Map(
        Delegate(ThroughLinks),
        RunPython('format_nih_url', ctx.row.APPLICATION_ID),
        RunPython('format_foa_url', ctx.row.FOA_NUMBER)
    )
    tags = Map(
        Delegate(ThroughTags),
        Maybe(ctx.row.PROJECT_TERMSX, 'TERM')
    )
    awards = Map(
        Delegate(ThroughAwards),
        ctx.row
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
        foa_number = ctx.row.FOA_NUMBER
        full_project_number = ctx.row.FULL_PROJECT_NUM
        nih_spending_cats = ctx.row.NIH_SPENDING_CATS
        organization_city = ctx.row.ORG_CITY
        organization_country = ctx.row.ORG_COUNTRY
        organization_dept = ctx.row.ORG_DEPT
        organization_district = ctx.row.ORG_DISTRICT
        organization_duns = ctx.row.ORG_DUNS
        organization_fips = ctx.row.ORG_FIPS
        organization_name = ctx.row.ORG_NAME
        organization_state = ctx.row.ORG_STATE
        organization_zip = ctx.row.ORG_ZIPCODE
        phr = ctx.row.PHR
        project_start = ctx.row.PROJECT_START
        project_end = ctx.row.PROJECT_END
        serial_number = ctx.row.SERIAL_NUMBER
        study_section = ctx.row.STUDY_SECTION
        study_section_name = ctx.row.STUDY_SECTION_NAME
        subproject_id = ctx.row.SUBPROJECT_ID
        suffix = ctx.row.SUFFIX
        support_year = ctx.row.SUPPORT_YEAR
        total_cost = ctx.row.TOTAL_COST
        total_cost_subproject = ctx.row.TOTAL_COST_SUB_PROJECT
