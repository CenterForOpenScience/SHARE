import re

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


class Link(Parser):
    url = ctx
    type = Static('provider')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Award(Parser):

    def get_award_amount(self, award_info):
        award = award_info.split('\n')[0]
        award_amount = award.split(':')[1]
        amount = re.findall(r'\d+', award_amount)
        return amount[0]

    def get_award_type(self, award_info):
        award_type = award_info.split('\n')[1]
        return award_type

    # The amount of the award provided by the funding NIH Institute(s) or Center(s)
    award = RunPython('get_award_amount', ctx)

    # The funding mechanism for this award, i.e.
    # one of the three main catgegories defined here: http://grants.nih.gov/grants/glossary.htm#Mechanism
    description = RunPython('get_award_type', ctx)


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class Funder(Parser):

    funding_ics_info = {
        'CC': {
            'full_name': 'Clinical Center',
            'organizational_code': 'CC'
        },
        'CSR': {
            'full_name': 'Center for Scientific Review',
            'organizational_code': 'RG'
        },
        'CIT': {
            'full_name': 'Center for Information Technology',
            'organizational_code': 'CIT'
        },
        'FIC': {
            'full_name': 'John E. Fogarty International Center',
            'organizational_code': 'TW'
        },
        'NCATS': {
            'full_name': 'National Center for Advancing Translational Sciences (NCATS)',
            'organizational_code': 'TR'
        },
        'NCCIH': {
            'full_name': 'National Center for Complementary and Integrative Health',
            'organizational_code': 'AT'
        },
        'NCI': {
            'full_name': 'National Cancer Institute',
            'organizational_code': 'CA'
        },
        'NCRR': {
            'full_name': 'National Center for Research Resources',
            'organizational_code': 'RR'
        },
        'NEI': {
            'full_name': 'National Eye Institute',
            'organizational_code': 'EY'
        },
        'NHGRI': {
            'full_name': 'National Human Genome Research Institute',
            'organizational_code': 'HG'
        },
        'NHLBI': {
            'full_name': 'National Heart, Lung, and Blood Institute',
            'organizational_code': 'HL'
        },
        'NIA': {
            'full_name': 'National Institute on Aging',
            'organizational_code': 'AG'
        },
        'NIAAA': {
            'full_name': 'National Institute on Alcohol Abuse and Alcoholism',
            'organizational_code': 'AA'
        },
        'NIAID': {
            'full_name': 'National Institute of Allergy and Infectious Diseases',
            'organizational_code': 'AI'
        },
        'NIAMS': {
            'full_name': 'National Institute of Arthritis and Musculoskeletal and Skin Diseases',
            'organizational_code': 'AR'
        },
        'NIBIB': {
            'full_name': 'National Institute of Biomedical Imaging and Bioengineering',
            'organizational_code': 'EB'
        },
        'NICHD': {
            'full_name': 'Eunice Kennedy Shriver National Institute of Child Health and Human Development',
            'organizational_code': 'HD'
        },
        'NIDA': {
            'full_name': 'National Institute on Drug Abuse',
            'organizational_code': 'DA'
        },
        'NIDCD': {
            'full_name': 'National Institute on Deafness and Other Communication Disorders',
            'organizational_code': 'DC'
        },
        'NIDCR': {
            'full_name': 'National Institute of Dental and Craniofacial Research',
            'organizational_code': 'DE'
        },
        'NIDDK': {
            'full_name': 'National Institute of Diabetes and Digestive and Kidney Diseases',
            'organizational_code': 'DK'
        },
        'NIEHS': {
            'full_name': 'National Institute of Environmental Health Sciences',
            'organizational_code': 'ES'
        },
        'NIGMS': {
            'full_name': 'National Institute of General Medical Sciences',
            'organizational_code': 'GM'
        },
        'NIMH': {
            'full_name': 'National Institute of Mental Health',
            'organizational_code': 'MH'
        },
        'NIMHD': {
            'full_name': 'National Institute on Minority Health and Health Disparities',
            'organizational_code': 'MD'
        },
        'NINDS': {
            'full_name': 'National Institute of Neurological Disorders and Stroke',
            'organizational_code': 'NS'
        },
        'NINR': {
            'full_name': 'National Institute of Nursing Research',
            'organizational_code': 'NR'
        },
        'NLM': {
            'full_name': 'National Library of Medicine',
            'organizational_code': 'LM'
        },
        'OD': {
            'full_name': 'Office of the Director',
            'organizational_code': 'OD'
        }
    }

    def get_funding_ic_full_name(self, funding_info):
        ic_acronym = funding_info.split(':')[0]
        ic_info = self.funding_ics_info.get(ic_acronym)
        if ic_info:
            return ic_info.get('full_name')
        return ic_acronym

    def get_funding_ic_identifier(self, funding_info):
        ic_acronym = funding_info.split(':')[0]
        ic_info = self.funding_ics_info.get(ic_acronym)
        if ic_info:
            return ic_info.get('organizational_code')
        return ic_acronym

    # The full name of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    name = RunPython('get_funding_ic_full_name', ctx)

    # The organizational code of the IC, as defined here: http://grants.nih.gov/grants/glossary.htm#InstituteorCenter(IC)
    community_identifier = RunPython('get_funding_ic_identifier', ctx)


class Association(Parser):
    entity = Delegate(Funder, ctx)


class CreativeWork(Parser):

    PROJECT_BASE_URL = 'https://projectreporter.nih.gov/project_info_description.cfm?aid={}'
    FOA_BASE_URL = 'https://grants.nih.gov/grants/guide/pa-files/{}.html'

    def format_nih_url(self, id):
        return self.PROJECT_BASE_URL.format(id)

    def format_foa_url(self, foa_number):
        return self.FOA_BASE_URL.format(foa_number)

    title = ctx.row.PROJECT_TITLE
    contributors = Map(
        Delegate(Contributor),
        ctx.row.PIS.PI
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
    funders = Map(
        Delegate(Association),
        ctx.row.FUNDING_ICs
    )
    awards = Map(
        Delegate(ThroughAwards),
        Join(
            Concat(
                ctx.row.FUNDING_ICs,
                ctx.row.FUNDING_MECHANISM
            ),
            '\n'
        )
    )


    class Extra:
        activity = ctx.row.ACTIVITY
        administering_ic = ctx.row.ADMINISTERING_IC
        application_id = ctx.row.APPLICATION_ID
        arra_funded = ctx.row.ARRA_FUNDED
        award_notice_date = ctx.row.AWARD_NOTICE_DATE
        budget_start = ctx.row.BUDGET_START
        budget_end = ctx.row.BUDGET_END
        cfda_code = ctx.row.CFDA_CODE
        core_project_number = ctx.row.CORE_PROJECT_NUM
        ed_inst_type = ctx.row.ED_INST_TYPE
        fiscal_year = ctx.row.FY
        foa_number = ctx.row.FOA_NUMBER
        full_project_number = ctx.row.FULL_PROJECT_NUM
        # funding_ics = ctx.row.FUNDING_ICs
        # funding_mechanism = ctx.row.FUNDING_MECHANISM
        ic_name = ctx.row.IC_NAME
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
        program_officer_name = ctx.row.PROGRAM_OFFICER_NAME
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
