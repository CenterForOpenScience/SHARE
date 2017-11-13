from collections import OrderedDict

import json

from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser


class AgentIdentifier(Parser):
    uri = tools.IRI(ctx)


class WorkIdentifier(Parser):
    uri = ctx


class Organization(Parser):
    name = ctx


class Publisher(Parser):
    agent = tools.Delegate(Organization, ctx)


class Institution(Parser):
    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(Institution)


class Person(Parser):
    given_name = tools.ParseName(tools.Try(ctx.name)).first
    family_name = tools.ParseName(tools.Try(ctx.name)).last
    identifiers = tools.Map(tools.Delegate(AgentIdentifier), tools.Try(ctx.email))


class Creator(Parser):
    agent = tools.Delegate(Person, ctx)


class Subject(Parser):
    name = ctx


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


def process_keywords(text):
    text = json.loads(text)
    text = [item for item in text if item]
    return text


class Registration(Parser):
    title = tools.Try(ctx['general-information']['title'])
    description = tools.Try(ctx['additional-trial-info']['abstract'])
    date_updated = tools.ParseDate(tools.Try(ctx['general-information']['last-updated']))
    date_published = tools.ParseDate(tools.Try(ctx['general-information']['published-at']))
    related_agents = tools.Map(tools.Delegate(Creator), tools.Try(ctx.pi))
    identifiers = tools.Map(
        tools.Delegate(WorkIdentifier),
        tools.Try(tools.IRI(ctx['general-information']['url'])),
    )
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Subjects(
            tools.RunPython(
                process_keywords,
                tools.Try(ctx['additional-trial-info']['keywords']),
            )
        )
    )
    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Concat(
            tools.RunPython(
                process_keywords,
                tools.Try(ctx['additional-trial-info']['keywords']),
            ),
            tools.Try(ctx['additional-trial-info']['status']),
            tools.Try(ctx['additional-trial-info']['jel-code'])
        )
    )

    class Extra:
        general_information = tools.Try(ctx['general-information'])
        additional_trial_information = tools.Try(ctx['additional-trial-info'])
        publication_data = tools.Try(ctx['data-publication'])
        primary_investigator = tools.Try(ctx['pi'])
        interventions = tools.Try(ctx['interventions'])
        outcomes = tools.Try(ctx['outcomes'])
        experimental_design = tools.Try(ctx['experimental-design'])
        experimental_characteristics = tools.Try(ctx['experimental-characteristics'])
        supporting_document_material = tools.Try(ctx['supporting-doc-material'])
        post_trial = tools.Try(ctx['post-trial'])
        reports_papers = tools.Try(ctx['reports-papers'])


class SCTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Registration

    def unwrap_data(self, data):
        loaded_data = json.loads(data, object_pairs_hook=OrderedDict)
        return self.process_record(loaded_data['record'])

    def process_record(self, record):
        data = {}
        general_info = {}
        if record[0]:
            general_info['title'] = record[0]
        if record[5]:
            general_info['RCT-ID'] = record[5]
        if record[4]:
            general_info['registered-on'] = record[4]
        if record[2]:
            general_info['last-updated'] = record[2]
        if record[1]:
            general_info['url'] = record[1]
        if record[3]:
            general_info['published-at'] = record[3]
        if general_info:
            data['general-information'] = general_info

        if record[6]:
            pi = record[6].split(',')
            data['pi'] = {'name': pi[0].strip(), 'email': pi[1].strip()}

        additional_trial_info = {}
        if record[7]:
            additional_trial_info['status'] = record[7]
        if record[8]:
            additional_trial_info['start-date'] = record[8]
        if record[9]:
            additional_trial_info['end-date'] = record[9]
        if record[10]:
            additional_trial_info['keywords'] = record[10]
        if record[11]:
            additional_trial_info['jel-code'] = record[11]
        if record[12]:
            additional_trial_info['abstract'] = record[12]
        if additional_trial_info:
            data['additional-trial-info'] = additional_trial_info

        interventions = {}
        if record[13]:
            interventions['start-date'] = record[13]
        if record[14]:
            interventions['end-date'] = record[14]
        if interventions:
            data['interventions'] = interventions

        outcomes = {}
        if record[15]:
            outcomes['outcome-end-points'] = record[15]
        if record[16]:
            outcomes['outcome-explanation'] = record[16]
        if outcomes:
            data['outcomes'] = outcomes

        experimental_design = {}
        if record[17]:
            experimental_design['experimental-design'] = record[17]
        if record[19]:
            experimental_design['rand-method'] = record[19]
        if record[20]:
            experimental_design['rand-unit'] = record[20]
        if experimental_design:
            data['experimental-design'] = experimental_design

        experimental_characteristics = {}
        if record[21]:
            experimental_characteristics['sample-size-number-clusters'] = record[21]
        if record[22]:
            experimental_characteristics['sample-size-number-observations'] = record[22]
        if record[23]:
            experimental_characteristics['sample-size-number-arms'] = record[23]
        if record[24]:
            experimental_characteristics['min-effect-size'] = record[24]
        if experimental_characteristics:
            data['experimental-characteristics'] = experimental_characteristics

        if record[25]:
            data['supporting-doc-material'] = record[25]

        post_trial = {}
        if record[27]:
            post_trial['intervention-complete-date'] = record[27]
        if record[28]:
            post_trial['data-collection-completion'] = record[28]
        if record[37]:
            post_trial['data-collection-completion-date'] = record[37]
        if post_trial:
            data['post-trial'] = post_trial

        data_publication = {}
        if record[33]:
            data_publication['public-data-url'] = record[33]
        if record[36]:
            data_publication['program-files-url'] = record[36]
        if data_publication:
            data['data-publication'] = data_publication

        reports_papers = {}
        if record[38]:
            reports_papers['relevant-reports'] = record[38]
        if record[39]:
            reports_papers['relevant-papers'] = record[39]
        if reports_papers:
            data['reports-papers'] = reports_papers

        return data
