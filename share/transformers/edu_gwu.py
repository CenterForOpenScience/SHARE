from share.transform.chain import ctx
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser
from share.transform.chain.soup import SoupXMLTransformer, SoupXMLDict, Soup


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx['#text'])


class Agent(Parser):
    schema = tools.RunPython('get_type', ctx)
    name = Soup(ctx, itemprop='name')['#text']

    def get_type(self, obj):
        return {
            'http://schema.org/Person': 'Person',
            'http://schema.org/Organization': 'Organization',
        }[obj.soup['itemtype']]


class Creator(Parser):
    order_cited = ctx('index')
    agent = tools.Delegate(Agent, ctx)


class Contributor(Parser):
    agent = tools.Delegate(Agent, ctx)


class Publisher(Parser):
    agent = tools.Delegate(Agent, ctx)


class Tag(Parser):
    name = ctx['#text']


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class CreativeWork(Parser):
    schema = tools.RunPython('get_type', ctx)

    title = tools.RunPython('get_title', ctx)
    description = Soup(ctx, 'p', class_='genericfile_description')['#text']
    date_published = tools.ParseDate(Soup(ctx, itemprop='datePublished')['#text'])
    date_updated = tools.ParseDate(Soup(ctx, itemprop='dateModified')['#text'])
    rights = tools.OneOf(
        tools.RunPython('get_rights_url', ctx),
        tools.RunPython('get_dd', ctx, 'Rights')['#text'],
        tools.Static(None)
    )
    language = tools.Try(tools.ParseLanguage(Soup(ctx, itemprop='inLanguage')['#text']))

    tags = tools.Map(tools.Delegate(ThroughTags), Soup(ctx, itemprop='keywords'))

    identifiers = tools.Map(
        tools.Delegate(WorkIdentifier),
        tools.Try(tools.RunPython('get_dd', ctx, 'Permanent Link')),
    )

    related_agents = tools.Concat(
        tools.Map(tools.Delegate(Creator), Soup(ctx, itemprop='creator')),
        tools.Map(tools.Delegate(Contributor), Soup(ctx, itemprop='contributor')),
        tools.Map(tools.Delegate(Publisher), Soup(ctx, itemprop='publisher')),
    )

    class Extra:
        gwu_unit = tools.RunPython('get_dd', ctx, 'GW Unit')['#text']
        related_url = tools.RunPython('get_dd', ctx, 'Related URL')['#text']
        previous_publication_information = tools.RunPython('get_dd', ctx, 'Previous Publication Information')['#text']
        depositor = tools.RunPython('get_dd', ctx, 'Depositor')['#text']
        characterization = tools.RunPython('get_dd', ctx, 'Characterization')['#text']

    def get_type(self, obj):
        return {
            'http://schema.org/CreativeWork': 'CreativeWork',
            'http://schema.org/Article': 'Article',
            'http://schema.org/Book': 'Book',
        }.get(obj.soup.find('div')['itemtype'], 'CreativeWork')

    def get_title(self, obj):
        title = obj.h1.soup
        title.find('span', class_='label').decompose()
        return title.get_text()

    def get_dd(self, obj, dt):
        dt_tag = obj.soup.find('dt', string=dt)
        if dt_tag:
            return SoupXMLDict(soup=dt_tag.find_next_sibling('dd'))
        return None

    def get_rights_url(self, obj):
        dd = self.get_dd(obj, 'Rights')
        return dd.soup.find('i', class_='glyphicon-new-window').parent['href']


class GWScholarSpaceTransformer(SoupXMLTransformer):
    VERSION = 1
    root_parser = CreativeWork
