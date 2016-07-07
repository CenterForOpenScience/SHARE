from share.normalize import *


class Link(Parser):
    pass


class ThroughLinks(Parser):
    pass


class Person(Parser):
    pass


class Contributor(Parser):
    pass


class Tag(Parser):
    pass


class ThroughTags(Parser):
    pass


class Publisher(Parser):
    pass


class Association(Parser):
    pass


class CreativeWork(Parser):
    # title = ctx.article.front['article-meta']['title-group']['article-title']
    # title = XPath(ctx, '//article-meta/title-group/article-title//string()')
    title = RunPython('parse_title', ctx)

    def parse_title(self, ctx):
        

    # links
    # contributors
    # date_updated
    # description
    # publishers
    # free_to_read_date
    # tags
    # rights

    class Extra:
        pass
        # article_categories
