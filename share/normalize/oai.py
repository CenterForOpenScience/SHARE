from share.normalize import links
from share.normalize import parsers
from share.normalize.normalizer import Normalizer


# NOTE: Context is a thread local singleton
# It is asigned to ctx here just to keep a family interface
ctx = links.Context()


class OAIPerson(parsers.Parser):
    schema = 'Person'

    suffix = links.ParseName(ctx).suffix
    family_name = links.ParseName(ctx).last
    given_name = links.ParseName(ctx).first
    additional_name = links.ParseName(ctx).middle


class OAIContributor(parsers.Parser):
    schema = 'Contributor'
    Person = OAIPerson

    person = ctx
    cited_name = ctx
    order_cited = ctx['index']


class OAITag(parsers.Parser):
    schema = 'Tag'
    name = ctx


class OAIThroughTags(parsers.Parser):
    schema = 'ThroughTags'
    Tag = OAITag
    tag = ctx


class OAIManuscript(parsers.Parser):
    schema = 'Manuscript'
    Contributor = OAIContributor
    ThroughTags = OAIThroughTags

    # needs to be types
    # types = ctx.record.metadata('oai_dc:dc')('dc:type')['*']
    # tags = (
    #     ctx.record.metadata('oai_dc:dc')('dc:subject')['*'] +
    #     ctx.record.metadata('oai_dc:dc')('dc:type')['*']
    # )
    tags = ctx.record.metadata('oai_dc:dc')('dc:subject')['*']
    language = ctx.record.metadata('oai_dc:dc').maybe('dc:language')

    title = ctx.record.metadata('oai_dc:dc')('dc:title')
    rights = ctx.record.metadata('oai_dc:dc').maybe('dc:rights')
    contributors = ctx.record.metadata('oai_dc:dc')('dc:creator')['*']
    # contributors = (
    #     ctx.record.metadata('oai_dc:dc')('dc:creator')['*'] +
    #     ctx.record.metadata('oai_dc:dc')('dc:contributor')['*']
    # )
    description = links.Concat(ctx.record.metadata('oai_dc:dc')('dc:description')['*'])


class OAINormalizer(Normalizer):
    root_parser = OAIManuscript
