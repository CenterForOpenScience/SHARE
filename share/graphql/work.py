import graphene
import bleach

from graphene_django import DjangoObjectType

from project.settings import ALLOWED_TAGS

from share import models
from share.graphql.base import Identifier
from share.graphql.base import AbstractShareObject
from share.graphql.relations import AbstractAgentWorkRelation, AbstractWorkRelation


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
    tags = graphene.List(Tag, limit=graphene.Int(), offset=graphene.Int())

    total_related_agents = graphene.Int()
    related_agents = graphene.List(AbstractAgentWorkRelation, limit=graphene.Int(), offset=graphene.Int())

    total_incoming_work_relations = graphene.Int()
    incoming_work_relations = graphene.List(AbstractWorkRelation, limit=graphene.Int(), offset=graphene.Int())

    total_outgoing_work_relations = graphene.Int()
    outgoing_work_relations = graphene.List(AbstractWorkRelation, limit=graphene.Int(), offset=graphene.Int())

    @graphene.resolve_only_args
    def resolve_title(self):
        return bleach.clean(self.title, strip=True, tags=ALLOWED_TAGS)

    @graphene.resolve_only_args
    def resolve_description(self):
        return bleach.clean(self.description, strip=True, tags=ALLOWED_TAGS)

    @graphene.resolve_only_args
    def resolve_identifiers(self):
        return self.identifiers.all()

    @graphene.resolve_only_args
    def resolve_tags(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.tags.all()[offset:limit]

    @graphene.resolve_only_args
    def resolve_total_related_agents(self):
        return self.agent_relations.exact_count()

    @graphene.resolve_only_args
    def resolve_related_agents(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.agent_relations.all()[offset:limit]

    @graphene.resolve_only_args
    def resolve_total_incoming_work_relations(self):
        return self.incoming_creative_work_relations.exact_count()

    @graphene.resolve_only_args
    def resolve_incoming_work_relations(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.incoming_creative_work_relations.all()[offset:limit]

    @graphene.resolve_only_args
    def resolve_total_outgoing_work_relations(self):
        return self.outgoing_creative_work_relations.exact_count()

    @graphene.resolve_only_args
    def resolve_outgoing_work_relations(self, limit=None, offset=None):
        if limit:
            offset = (offset or 0) + limit
        return self.outgoing_creative_work_relations.all()[offset:limit]


for klass in models.CreativeWork.get_type_classes():
    locals()[klass.__name__] = type(klass.__name__, (DjangoObjectType, ), {
        'Meta': type('Meta', (), {'model': klass, 'interfaces': (AbstractShareObject, AbstractCreativeWork, )})
    })
