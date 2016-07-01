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
    title = ctx.xpath("str[@name='title_display']")('str')('#text')
    description = ctx.xpath("arr[@name='abstract']/str")('str')
    contributors = ctx.xpath("arr[@name='author_display']")('arr')('str')['*']
    published = ctx.xpath("date[@name='publication_date']")('date')('#text')
    doi = ctx.xpath("str[@name='id']")('str')('#text')
