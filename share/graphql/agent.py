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

    total_related_works = graphene.Int()
    related_works = graphene.List(AbstractAgentWorkRelation, limit=graphene.Int(), offset=graphene.Int())

    total_incoming_agent_relations = graphene.Int()
    incoming_agent_relations = graphene.List(AbstractAgentRelation, limit=graphene.Int(), offset=graphene.Int())

    total_outgoing_agent_relations = graphene.Int()
    outgoing_agent_relations = graphene.List(AbstractAgentRelation, limit=graphene.Int(), offset=graphene.Int())

    @graphene.resolve_only_args
    def resolve_identifiers(self):
        return self.identifiers.exclude(scheme='mailto').exclude(same_as__isnull=False)

    @graphene.resolve_only_args
    def resolve_total_related_works(self):
        return self.work_relations.exclude(same_as__isnull=False).count()

    @graphene.resolve_only_args
    def resolve_related_works(self, offset=None, limit=10):
        limit = (offset or 0) + limit
        return self.work_relations.exclude(same_as__isnull=False)[offset:limit]

    @graphene.resolve_only_args
    def resolve_total_incoming_agent_relations(self):
        return self.incoming_agent_relations.exclude(same_as__isnull=False).count()

    @graphene.resolve_only_args
    def resolve_incoming_agent_relations(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.incoming_agent_relations.exclude(same_as__isnull=False)[offset:limit]

    @graphene.resolve_only_args
    def resolve_total_outgoing_agent_relations(self):
        return self.outgoing_agent_relations.exclude(same_as__isnull=False).count()

    @graphene.resolve_only_args
    def resolve_outgoing_agent_relations(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.outgoing_agent_relations.exclude(same_as__isnull=False)[offset:limit]

for klass in models.Agent.get_type_classes():
    locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
        'Meta': type('Meta', (), {'model': klass, 'interfaces': (AbstractShareObject, AbstractAgent, )})
    })
