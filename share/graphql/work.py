import graphene

from graphene_django import DjangoObjectType

from share import models
from share.graphql.base import Identifier
from share.graphql.base import AbstractShareObject
from share.graphql.relations import AbstractAgentWorkRelation


class Tag(DjangoObjectType):
    tagged_works = graphene.List(lambda: AbstractCreativeWork, limit=graphene.Int(), offset=graphene.Int())

    class Meta:
        model = models.Tag

    @graphene.resolve_only_args
    def resolve_tagged_works(self, limit=50, offset=0):
        return models.AbstractCreativeWork.objects.filter(tags__name=self.name)[offset:offset + limit]


class AbstractCreativeWork(AbstractShareObject):
    title = graphene.String()
    description = graphene.String()

    # raw_data = graphene.List(RawData)
    identifiers = graphene.List(Identifier)
    related_agents = graphene.List(AbstractAgentWorkRelation, limit=graphene.Int(), offset=graphene.Int())
    tags = graphene.List(Tag, limit=graphene.Int(), offset=graphene.Int())

    @graphene.resolve_only_args
    def resolve_identifiers(self):
        return self.identifiers.all()

    @graphene.resolve_only_args
    def resolve_tags(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.tags.all()[offset:limit]

    @graphene.resolve_only_args
    def resolve_related_agents(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.agent_relations.all()[offset:limit]


for klass in models.CreativeWork.get_type_classes():
    locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
        'Meta': type('Meta', (), {'model': klass, 'interfaces': (AbstractShareObject, AbstractCreativeWork, )})
    })
