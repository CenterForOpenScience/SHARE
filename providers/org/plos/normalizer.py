from share.normalize import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = ctx
    cited_name = ctx
    order_cited = ctx['index']


class CreativeWork(Parser):
    title = ctx.xpath("str[@name='title_display']")[0].text()
    description = ctx.xpath("arr[@name='abstract']/str")[0].text()
    contributors = ctx.xpath("arr[@name='author_display']/str")['*'].text()
    published = ctx.xpath("date[@name='publication_date']")[0].text()
    doi = ctx.xpath("str[@name='id']")[0].text()
