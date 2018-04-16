import graphene

from django.conf import settings

from elasticsearch import Elasticsearch

from share import models
from share.graphql.agent import AbstractAgent
from share.graphql.base import Source
from share.graphql.base import User
from share.graphql.base import AbstractShareObject
from share.graphql.elasticsearch import ElasticSearchAggregation
from share.graphql.elasticsearch import ElasticSearchQuery
from share.graphql.elasticsearch import ElasticSearchResult
from share.graphql.work import AbstractCreativeWork
from share.util import IDObfuscator


class Query(graphene.ObjectType):

    search = graphene.Field(ElasticSearchResult, args={
        'aggregations': graphene.List(ElasticSearchAggregation),
        'from': graphene.Int(description='Retrieve hits from a certain offset. Defaults to 0.'),
        'query': ElasticSearchQuery(),
        'size': graphene.Int(description='The number of hits to return. Defaults to 10.'),
        'type': graphene.String(required=True),  # TODO Make into an enum
    }, description='Query the SHARE data set via Elasticsearch')

    me = graphene.Field(User)
    sources = graphene.List(Source, limit=graphene.Int(), offset=graphene.Int())

    client = Elasticsearch(settings.ELASTICSEARCH['URL'], retry_on_timeout=True, timeout=30)

    agent = graphene.Field(AbstractAgent, id=graphene.String(), resolver=IDObfuscator.resolver)
    creative_work = graphene.Field(AbstractCreativeWork, id=graphene.String(), resolver=IDObfuscator.resolver)
    share_object = graphene.Field(AbstractShareObject, id=graphene.String(), resolver=IDObfuscator.resolver)

    def resolve_me(self, args, context, info):
        return context.user

    @graphene.resolve_only_args
    def resolve_sources(self, limit=25, offset=0):
        return models.Source.objects.exclude(icon='').order_by('long_title')[offset:offset + limit]

    def resolve_search(self, args, context, info):
        args.setdefault('from', 0)
        args.setdefault('size', 10)

        resp = Query.client.search(index=settings.ELASTICSEARCH['INDEX'], doc_type=args.pop('type'), body=args)

        del resp['_shards']  # No need to expose server information

        return ElasticSearchResult(**resp)
