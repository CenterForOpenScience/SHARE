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

    title = links.Trim(ctx.metadata.dc.title.text())
    contributors = ctx.metadata.dc.creator['*']
    description = links.Trim(links.Concat(ctx.metadata.dc.description['*'].text()))


class OAINormalizer(Normalizer):
    root_parser = OAIManuscript
