import graphene

from share.graphql.fields import JSONField


class ElasticSearchQueryString(graphene.InputObjectType):
    query = graphene.String(required=True)


class ElasticSearchTermsAggregation(graphene.InputObjectType):
    field = graphene.String(required=True)
    size = graphene.Int(required=True)


class ElasticSearchAggregation(graphene.InputObjectType):
    name = graphene.String(required=True)
    terms = ElasticSearchTermsAggregation()


class ElasticSearchQuery(graphene.InputObjectType):
    query_string = ElasticSearchQueryString()


class ElasticSearchHit(graphene.ObjectType):
    _id = graphene.String(name='_id')
    _type = graphene.String(name='_type')
    _score = graphene.String(name='_score')
    _index = graphene.String(name='_index')
    _source = JSONField(name='_source')


class ElasticSearchHits(graphene.ObjectType):
    total = graphene.Int(description='The total number of documents matching the search criteria.')
    max_score = graphene.Int(name='max_score', description='')
    hits = graphene.List(ElasticSearchHit, description='An array of the actual results.')

    def resolve_hits(self, args, context, info):
        return (ElasticSearchHit(**hit) for hit in self.hits)


class ElasticSearchResult(graphene.ObjectType):
    hits = graphene.Field(ElasticSearchHits, description='The search results.')
    took = graphene.Int(description='The time, in milliseconds, for Elasticsearch to execute the search.')
    timed_out = graphene.Boolean(name='timed_out', description='Indicated whether this search timed out.')

    def resolve_hits(self, args, context, info):
        return ElasticSearchHits(**self.hits)
