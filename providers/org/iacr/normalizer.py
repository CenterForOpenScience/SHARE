from share.normalize import ctx, Parser, RunPython, Map, Delegate, ParseName


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
    title = RunPython('parse_title', ctx.item.title)
    description = ctx.item.description

    contributors = Map(
        Delegate(Contributor),
        RunPython('parse_contributors', ctx.item.title)
    )

    links = Map(
        Delegate(ThroughLinks),
        ctx.item.link
    )

    def parse_title(self, title):
        return title.split(', by ')[0]

    def parse_contributors(self, title):
        return title.split(', by ')[1].split(' and ')
