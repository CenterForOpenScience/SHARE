import graphene

from graphene_django import DjangoObjectType

from share import models
from share.graphql.fields import JSONField


class Source(DjangoObjectType):
    title = graphene.String()
    icon = graphene.String()

    class Meta:
        model = models.Source
        only_fields = ('id', 'home_page', )

    @classmethod
    def resolve_id(cls, instance, context, request, info):
        return instance.name

    @classmethod
    def resolve_title(cls, instance, context, request, info):
        return instance.long_title

    @classmethod
    def resolve_icon(cls, instance, context, request, info):
        return instance.icon.url if instance.icon else None


class AbstractShareObject(graphene.Interface):
    _implementers = set()

    id = graphene.String()
    types = graphene.List(graphene.String)
    extra = JSONField()
    sources = graphene.List(Source, limit=graphene.Int(), offset=graphene.Int())

    class Meta:
        name = 'ShareObject'

    @classmethod
    def implements(cls, type):
        cls._implementers.add(type)

    @classmethod
    def resolve_type(cls, instance, context, info):
        return info.schema.get_type(type(instance).__name__)

    @graphene.resolve_only_args
    def resolve_types(self):
        types = []
        for parent in self.__class__.mro():
            if not parent._meta.proxy:
                break
            types.append(parent._meta.verbose_name.title())
        return types

    @graphene.resolve_only_args
    def resolve_extra(self):
        if self.extra_id:
            return self.extra.data
        return {}

    @graphene.resolve_only_args
    def resolve_sources(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return [user.source for user in self.sources.select_related('source').exclude(source__icon='').exclude(source__is_deleted=True)[offset:limit]]


class User(DjangoObjectType):
    class Meta:
        model = models.ShareUser


class Identifier(graphene.ObjectType):
    uri = graphene.String()
    host = graphene.String()
    scheme = graphene.String()
