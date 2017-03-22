from share.transform.chain import Parser, ctx, links as tools, ChainTransformer

LINK_FORMAT = 'http://www.researchregistry.com/browse-the-registry.html#home/registrationdetails/{}/'

FIELDS = {
    'uin': 'field_21',
    'registration date': 'field_2',
    'title': 'field_7',
    'questions and objectives': 'field_75',
    'summary': 'field_78',
    'study type': 'field_72',
    'study type other': 'field_14',
    'primary investigator': 'field_3',
    'other investigator': 'field_4',
    'additional investigators': 'field_94',
    'contact details': 'field_5',
    'email': 'field_97',
    'participating institutions': 'field_68',
    'countries of recruitment': 'field_10',
    'funders': 'field_9',
    'health conditions or problems studied': 'field_11',
    'patient population': 'field_29',
    'interventions': 'field_12',
    'inclusion criteria': 'field_13',
    'exclusion criteria': 'field_70',
    'control or comparators': 'field_28',
    'primary outcomes': 'field_18',
    'key secondary outcomes': 'field_19',
    'target sample size': 'field_16',
    'recruitment status': 'field_79',
    'other recruitment status': 'field_17',
    'first enrollment date': 'field_15',
    'expected enrollment completion date': 'field_80',
    'expected research completion date': 'field_73',
    'ethical approval': 'field_81',
    'ethical approval details': 'field_63',
    'ethical committee judgment': 'field_62',
    'data': 'field_64',
    'published paper identifier': 'field_37',
    'study website': 'field_30',
    'study results': 'field_89',
    'user': 'field_66',
}


class Person(Parser):
    family_name = ctx['last']
    given_name = ctx['first']


class FullNamePerson(Parser):
    schema = 'person'
    name = ctx


class PrincipalInvestigator(Parser):
    agent = tools.Delegate(Person, ctx)


class OtherInvestigator(Parser):
    schema = 'contributor'
    agent = tools.Delegate(Person, ctx)


class AdditionalInvestigator(Parser):
    schema = 'contributor'
    agent = tools.Delegate(FullNamePerson, ctx)


class WorkIdentifier(Parser):
    uri = ctx


class Registration(Parser):
    title = ctx[FIELDS['title']]
    description = ctx[FIELDS['summary']]
    date_published = tools.ParseDate(ctx[FIELDS['registration date']].timestamp)
    date_updated = tools.ParseDate(ctx[FIELDS['registration date']].timestamp)
    related_agents = tools.Concat(
        tools.Delegate(PrincipalInvestigator, ctx[FIELDS['primary investigator']]),
        tools.Delegate(OtherInvestigator, ctx[FIELDS['other investigator']]),
        tools.Map(
            tools.Delegate(AdditionalInvestigator),
            tools.RunPython('split_names', ctx[FIELDS['additional investigators']])
        )
    )
    identifiers = tools.Map(
        tools.Delegate(WorkIdentifier),
        tools.RunPython('get_link', ctx.id)
    )

    class Extra:
        registration_date = ctx[FIELDS['registration date']]
        questions_and_objectives = ctx[FIELDS['questions and objectives']]
        study_type = ctx[FIELDS['study type']]
        study_type_detail = ctx[FIELDS['study type other']]
        contact_details = ctx[FIELDS['contact details']]
        participating_institutions = ctx[FIELDS['participating institutions']]
        countries_of_recruitment = ctx[FIELDS['countries of recruitment']]
        funders = ctx[FIELDS['funders']]
        problems_studied = ctx[FIELDS['health conditions or problems studied']]
        patient_population = ctx[FIELDS['patient population']]
        interventions = ctx[FIELDS['interventions']]
        inclusion_criteria = ctx[FIELDS['inclusion criteria']]
        exclusion_criteria = ctx[FIELDS['exclusion criteria']]
        control_or_comparators = ctx[FIELDS['control or comparators']]
        primary_outcomes = ctx[FIELDS['primary outcomes']]
        key_secondary_outcomes = ctx[FIELDS['key secondary outcomes']]
        target_sample_size = ctx[FIELDS['target sample size']]
        recruitment_status = ctx[FIELDS['recruitment status']]
        other_recruitment_status = ctx[FIELDS['other recruitment status']]
        first_enrollment_date = ctx[FIELDS['first enrollment date']]
        expected_enrollment_completion_date = ctx[FIELDS['expected enrollment completion date']]
        expected_research_completion_date = ctx[FIELDS['expected research completion date']]
        ethical_approval = ctx[FIELDS['ethical approval']]
        ethical_approval_details = ctx[FIELDS['ethical approval details']]
        ethical_committee_judgment = ctx[FIELDS['ethical committee judgment']]
        data = ctx[FIELDS['data']]
        published_paper = ctx[FIELDS['published paper identifier']]
        study_website = ctx[FIELDS['study website']]
        study_results = ctx[FIELDS['study results']]

    def get_link(self, id):
        return LINK_FORMAT.format(id)

    def split_names(self, obj):
        if not obj:
            return None
        return obj.split(',')


class RRTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Registration
