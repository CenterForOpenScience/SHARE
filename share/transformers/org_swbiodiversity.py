from bs4 import BeautifulSoup

from share.transform.chain import ctx
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser
from share.transform.chain.soup import SoupXMLTransformer
from share.transform.chain.utils import contact_extract


class AgentIdentifier(Parser):
    uri = tools.IRI(ctx)


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx)


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


class Dataset(Parser):
    title = tools.Try(ctx['title'])
    description = tools.Try(ctx['description'])

    rights = tools.Try(
        tools.Join(
            tools.Concat(
                tools.Try(ctx['access-rights']),
                tools.Try(ctx['usage-rights'])
            )
        )
    )

    related_agents = tools.Map(tools.Delegate(Creator), tools.Try(ctx.contact))

    class Extra:
        access_rights = tools.Try(ctx['access-rights'])
        usage_rights = tools.Try(ctx['usage-rights'])
        collection_statistics = tools.Try(ctx['collection-statistics'])
        management = tools.Try(ctx['management'])
        collection_type = tools.Try(ctx['collection-type'])
        last_update = tools.ParseDate(tools.Try(ctx['last-update']))


class SWTransformer(SoupXMLTransformer):
    VERSION = 1
    root_parser = Dataset

    def unwrap_data(self, input_data, **kwargs):
        record = BeautifulSoup(input_data, 'lxml').html
        data = {}
        title = self.extract_text(record.h1)
        if title:
            data['title'] = title
        start = record.div.div
        description = self.extract_text(start.find_next())
        if description:
            data['description'] = description

        if start:
            body = start.find_all_next(style='margin-top:5px;')
            body = list(map(self.extract_text, body))

            for entry in body:

                if 'Contact:' in entry:
                    data['contact'] = contact_extract(entry)

                if 'Collection Type:' in entry:
                    collection_type = entry.replace('Collection Type: ', '')
                    data['collection-type'] = collection_type

                if 'Management:' in entry:
                    management = entry.replace('Management: ', '')
                    if 'Last Update:' in management:
                        management_update = management.split('Last Update:', 1)
                        management = management_update[0]
                        last_update = management_update[1]
                        if last_update:
                            data['last-update'] = last_update.strip()
                    data['management'] = management.strip()

                if 'Usage Rights:' in entry:
                    usage_rights = entry.replace('Usage Rights: ', '')
                    data['usage-rights'] = usage_rights

                if 'Access Rights' in entry or 'Rights Holder:' in entry:
                    access_rights = entry.replace('Access Rights: ', '').replace('Rights Holder: ', '')
                    data['access-rights'] = access_rights

            collection_statistics = start.find_all_next('li')
            collection_statistics = list(map(self.extract_text, collection_statistics))
            data['collection-statistics'] = self.process_collection_stat(collection_statistics)

        return data

    def extract_text(self, text):
        return text.text.strip()

    def process_collection_stat(self, list_values):
        stat = {}
        for item in list_values:
            value = item.split()
            stat[item.replace(str(value[0]), '').strip()] = value[0]
        return stat
