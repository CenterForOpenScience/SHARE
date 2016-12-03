import graphene

from graphene_django import DjangoObjectType

from share import models
from share.graphql.base import AbstractShareObject


def Agent():
    from share.graphql.agent import AbstractAgent
    return AbstractAgent


def CreativeWork():
    from share.graphql.work import AbstractCreativeWork
    return AbstractCreativeWork


class AbstractWorkRelation(AbstractShareObject):
    subject = graphene.Field(CreativeWork)
    related = graphene.Field(CreativeWork)

    @graphene.resolve_only_args
    def resolve_related(self):
        return self.related

    @graphene.resolve_only_args
    def resolve_subject(self):
        return self.subject


class AbstractAgentRelation(AbstractShareObject):
    subject = graphene.Field(Agent)
    related = graphene.Field(Agent)

    @graphene.resolve_only_args
    def resolve_related(self):
        return self.related

    @graphene.resolve_only_args
    def resolve_subject(self):
        return self.subject


class AbstractAgentWorkRelation(AbstractShareObject):
    cited_as = graphene.String()
    agent = graphene.Field(Agent)
    creative_work = graphene.Field(CreativeWork)

    @graphene.resolve_only_args
    def resolve_agent(self):
        return self.agent


for base, interface in ((models.AgentRelation, AbstractAgentRelation), (models.WorkRelation, AbstractWorkRelation), (models.AgentWorkRelation, AbstractAgentWorkRelation)):
    for klass in base.get_type_classes():
        locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
            'Meta': type('Meta', (), {'model': klass, 'interfaces': (interface, )})
        })
