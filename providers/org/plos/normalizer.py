from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class CreativeWork(Parser):
    title = XPath(ctx, "str[@name='title_display']").str['#text']
    description = XPath(ctx, "arr[@name='abstract']/str").str
    contributors = Map(
        Delegate(Contributor),
        XPath(ctx, "arr[@name='author_display']").arr.str
    )
    published = ParseDate(XPath(ctx, "date[@name='publication_date']").date['#text'])
    # doi = ctx.xpath("str[@name='id']").str['#text']
