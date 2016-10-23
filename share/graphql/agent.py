import graphene

from graphene_django import DjangoObjectType

from share import models
from share.graphql.base import Identifier
from share.graphql.base import AbstractShareObject


class AbstractAgent(AbstractShareObject):
    name = graphene.String()
    identifiers = graphene.List(Identifier)

    @graphene.resolve_only_args
    def resolve_identifiers(self):
        return self.identifiers.all()


for klass in models.Agent.get_type_classes():
    locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
        'Meta': type('Meta', (), {'model': klass, 'interfaces': (AbstractShareObject, AbstractAgent, )})
    })
