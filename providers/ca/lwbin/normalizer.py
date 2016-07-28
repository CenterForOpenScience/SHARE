from share.normalize import *


class Tag(Parser):
    name = ctx.name


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if '130.179.67.140' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):

    def get_free_to_read_date(self, ctx):
        is_open = ctx.get('isopen')
        return ctx.get('metadata_created') if is_open else None

    title = ctx.title
    description = ctx.notes
    date_updated = ParseDate(ctx.metadata_modified)
    free_to_read_date = RunPython('get_free_to_read_date', ctx)
    links = Map(Delegate(ThroughLinks), Maybe(ctx, 'url'))
    tags = Map(Delegate(ThroughTags), ctx.tags)

    class Extra:
        authors = Concat(ctx.author, ctx.author_email)
        creator_user_id = ctx.creator_user_id
        groups = ctx.groups
        maintainer = ctx.maintainer
        maintainer_email = ctx.maintainer_email
        metadata_created = ParseDate(ctx.metadata_created)
        name = ctx.name
        number_of_resources = Maybe(ctx, 'number_of_resources')
        number_of_tags = Maybe(ctx, 'number_of_tags')
        revision_timestamp = ParseDate(ctx.revision_timestamp)
        state = ctx.state
        type = ctx.type
        version = ctx.version
