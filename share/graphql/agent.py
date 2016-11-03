import graphene

from graphene_django import DjangoObjectType

from share import models
from share.graphql.base import Identifier
from share.graphql.base import AbstractShareObject
from share.graphql.relations import AbstractAgentRelation
from share.graphql.relations import AbstractAgentWorkRelation


class AbstractAgent(AbstractShareObject):
    name = graphene.String()
    identifiers = graphene.List(Identifier)

    related_agents = graphene.List(AbstractAgentRelation, limit=graphene.Int(), offset=graphene.Int())
    related_works = graphene.List(AbstractAgentWorkRelation, limit=graphene.Int(), offset=graphene.Int())

    @graphene.resolve_only_args
    def resolve_identifiers(self):
        return self.identifiers.all()

    @graphene.resolve_only_args
    def resolve_related_agents(self, offset=None, limit=10):
        limit = limit or (offset or 0) + limit
        return self.agent_relations.all()[offset:limit]

    @graphene.resolve_only_args
    def resolve_related_works(self, offset=None, limit=10):
        limit = limit or (offset or 0) + limit
        return self.work_relations.all()[offset:limit]


for klass in models.Agent.get_type_classes():
    locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
        'Meta': type('Meta', (), {'model': klass, 'interfaces': (AbstractShareObject, AbstractAgent, )})
    })
