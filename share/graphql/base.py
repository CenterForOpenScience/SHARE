import graphene

from django.core.urlresolvers import reverse

from graphene_django import DjangoObjectType

from share import models
from share.util import IDObfuscator
from share.graphql.fields import JSONField


class Source(DjangoObjectType):
    title = graphene.String()
    favicon = graphene.String()
    date_added = graphene.String()

    class Meta:
        model = models.ShareUser
        only_fields = ('id', 'home_page', 'is_active', )

    @classmethod
    def resolve_id(cls, instance, context, request, info):
        return instance.robot.replace('providers.', '', 1)

    @classmethod
    def resolve_title(cls, instance, context, request, info):
        return instance.long_title

    @classmethod
    def resolve_favicon(cls, instance, context, request, info):
        return reverse('user_favicon', kwargs={'username': instance.username})

    @classmethod
    def resolve_date_added(cls, instance, context, request, info):
        return instance.date_joined.isoformat()


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
    def resolve_id(self):
        return IDObfuscator.encode(self)

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
        return self.sources.all()[offset:limit]

    # def __getattr__(self, attr):
        # TODO if looking for resolve_*, return a default getter method
        # for relationship fields, handle limit/offset and filter out non-null same_as
        # maybe implement default resolve_total_* for relationships, too


class User(DjangoObjectType):
    class Meta:
        model = models.ShareUser


class Identifier(graphene.ObjectType):
    uri = graphene.String()
    host = graphene.String()
    scheme = graphene.String()
