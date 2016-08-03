from share.normalize import ctx, Parser, RunPython, XPath, Map, Delegate, ParseName


def text(obj):
    return obj.get('#text') or obj['italic']


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'eprint.iacr.org' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = ctx


class Tag(Parser):
    name = ctx


class CreativeWork(Parser):
    """
    Documentation for CrossRef's metadata can be found here:
    https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
    """

    title = RunPython('parse_title', XPath(ctx, '//title')['title'])
    description = XPath(ctx, '//description')['description']

    contributors = Map(
        Delegate(Contributor),
        RunPython('parse_contributors', XPath(ctx, '//title')['title'])
    )

    links = Map(
        Delegate(ThroughLinks),
        XPath(ctx, '//link')['link']
    )

    def parse_title(self, title):
        return title.split(', by ')[0]

    def parse_contributors(self, title):
        return title.split(', by ')[1].split(' and ')
