from share.normalize import *
from share.normalize.utils import format_address


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
    community_identifier = RunPython('filter_nil', ctx.ADMINISTERING_IC)

    def filter_nil(self, obj):
        if isinstance(obj, dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj

    class Extra:
        funding_ics = ctx.FUNDING_ICs
        funding_mechanism = ctx.FUNDING_MECHANISM


class ThroughAwardEntities(Parser):
    entity = Delegate(Funder, ctx)


class Award(Parser):
    # The amount of the award provided by the funding NIH Institute(s) or Center(s)
    description = RunPython('get_award_amount', ctx.FUNDING_ICs)
    entities = Map(Delegate(ThroughAwardEntities), ctx)

    class Extra:
        arra_funded = ctx.ARRA_FUNDED
        award_notice_date = ctx.AWARD_NOTICE_DATE

    def get_award_amount(self, award_info):
        if not award_info or (isinstance(award_info, dict) and award_info.get('@http://www.w3.org/2001/XMLSchema-instance:nil')):
            return None
        return award_info.split(':')[1].replace('\\', '')


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class Organization(Parser):
    name = ctx.ORG_NAME
    location = RunPython('format_address', ctx)

    class Extra:
        organization_duns = ctx.ORG_DUNS
        organization_fips = ctx.ORG_FIPS
        organization_dept = ctx.ORG_DEPT
        organization_district = ctx.ORG_DISTRICT

    def format_address(self, doc):
        return format_address(
            self,
            city=doc.get('ORG_CITY'),
            state_or_province=doc.get('ORG_STATE'),
            postal_code=doc.get('ORG_ZIPCODE'),
            country=doc.get('ORG_COUNTRY')
        )


class Association(Parser):
    pass


class Project(Parser):
    PROJECT_BASE_URL = 'https://projectreporter.nih.gov/project_info_description.cfm?aid={}'
    FOA_BASE_URL = 'https://grants.nih.gov/grants/guide/pa-files/{}.html'

    title = ctx.row.PROJECT_TITLE
    contributors = Concat(
        Map(Delegate(Contributor), Maybe(ctx.row.PIS, 'PI')),
        Map(Delegate(ProgramOfficer), RunPython('filter_nil', ctx.row.PROGRAM_OFFICER_NAME))
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
    organizations = Map(
        Delegate(Association.using(entity=Delegate(Organization))),
        RunPython('maybe_org', ctx.row)
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

    def format_nih_url(self, id):
        return self.PROJECT_BASE_URL.format(id)

    def format_foa_url(self, foa_number):
        return self.FOA_BASE_URL.format(foa_number)

    def parse_awards(self, award_info):
        return [award for award in award_info.split(';')]

    def filter_nil(self, obj):
        if isinstance(obj, dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj

    def maybe_org(self, obj):
        if isinstance(obj.get('ORG_NAME'), dict) and obj.get('@http://www.w3.org/2001/XMLSchema-instance:nil'):
            return None
        return obj
