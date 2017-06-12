from share.transform.chain import *
from share.transform.chain.utils import force_text


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class AgentIdentifier(Parser):
    # email address
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class AffiliatedAgent(Parser):
    schema = GuessAgentType(ctx, default='organization')
    name = ctx


class IsAffiliatedWith(Parser):
    related = Delegate(AffiliatedAgent, ctx)


class Institution(Parser):
    name = OneOf(ctx.agency, ctx.facility.name, ctx)
    location = RunPython('get_location', Try(ctx.facility.address))

    class Extra:
        agency_class = Try(ctx.agency_class)

    def get_location(self, ctx):
        location = ""
        if 'country' in ctx:
            location += ctx['country'] + ': '
        if 'city' in ctx:
            location += ctx['city'] + ', '
        if 'state' in ctx:
            location += ctx['state'] + ' '
        return location


class Person(Parser):
    given_name = Maybe(ctx, 'first_name')
    family_name = Maybe(ctx, 'last_name')
    additional_name = Maybe(ctx, 'middle_name')

    identifiers = Map(Delegate(AgentIdentifier), Try(ctx.email))
    related_agents = Map(Delegate(IsAffiliatedWith), Try(ctx.affiliation))


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class Funder(Parser):
    agent = Delegate(Institution, ctx)


class Registration(Parser):
    title = OneOf(
        ctx.clinical_study.official_title,
        ctx.clinical_study.brief_title
    )
    description = Maybe(ctx.clinical_study, 'brief_summary')['textblock']

    date_published = Try(ParseDate(RunPython(force_text, ctx.clinical_study.firstreceived_date)))
    date_updated = Try(ParseDate(RunPython(force_text, ctx.clinical_study.lastchanged_date)))

    related_agents = Concat(
        Map(Delegate(Contributor), Maybe(ctx.clinical_study, 'overall_official')),
        Map(Delegate(Contributor), Maybe(ctx.clinical_study, 'overall_contact')),
        Map(Delegate(Contributor), Maybe(ctx.clinical_study, 'overall_contact_backup')),
        Map(Delegate(Funder),
            Concat(ctx.clinical_study.sponsors.lead_sponsor,
                   Maybe(ctx.clinical_study.sponsors, 'collaborator'),
                   RunPython('get_locations', Concat(Try(ctx.clinical_study.location)))))
    )

    tags = Map(Delegate(ThroughTags), Maybe(ctx.clinical_study, 'keyword'))

    identifiers = Concat(Map(Delegate(WorkIdentifier), Concat(
        ctx['clinical_study']['required_header']['url'],
        RunPython('format_url', ctx.clinical_study.id_info.nct_id, 'http://www.bioportfolio.com/resources/trial/'),
        RunPython('format_url', Try(ctx.clinical_study.reference.PMID), 'www.ncbi.nlm.nih.gov/pubmed/'))))

    class Extra:
        share_harvest_date = ctx.clinical_study.required_header.download_date
        org_study_id = ctx.clinical_study.id_info.org_study_id
        status = ctx.clinical_study.overall_status
        start_date = Try(ParseDate(RunPython(force_text, ctx.clinical_study.start_date)))
        completion_date = Try(ParseDate(RunPython(force_text, ctx.clinical_study.completion_date)))
        completion_date_type = Try(ctx.clinical_study.completion_date['@type'])
        study_type = ctx.clinical_study.study_type
        conditions = Try(ctx.clinical_study.condition)
        is_fda_regulated = Try(ctx.clinical_study.is_fda_regulated)
        is_section_801 = Try(ctx.clinical_study.is_section_801)
        citation = Try(ctx.clinical_study.reference.citation)

    def get_locations(self, locations):
        results = []
        for location in locations:
            if 'name' in location['facility']:
                results.append(location)
        return results

    def format_url(self, id, base):
        return base + id


class ClinicalTrialsTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Registration
