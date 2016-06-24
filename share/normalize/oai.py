from share.normalize import links
from share.normalize import parsers
from share.normalize.normalizer import Normalizer


# NOTE: Context is a thread local singleton
# It is asigned to ctx here just to keep a family interface
ctx = links.Context()


class OAIPerson(parsers.Parser):
    schema = 'Person'

    given_name = links.ParseName(ctx.text()).first
    family_name = links.ParseName(ctx.text()).last


class OAIContributor(parsers.Parser):
    schema = 'Contributor'
    Person = OAIPerson

    person = ctx


class OAIManuscript(parsers.Parser):
    schema = 'Manuscript'
    Contributor = OAIContributor

    title = links.Trim(ctx.metadata[0].dc[0].title[0].text())
    contributors = ctx.metadata[0].dc[0].creator['*']
    description = links.Trim(links.Concat(ctx.metadata[0].dc[0].description['*'].text()))


class OAINormalizer(Normalizer):
    root_parser = OAIManuscript
