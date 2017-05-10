import graphene

from share.graphql.query import Query
from share.graphql.base import AbstractShareObject


schema = graphene.Schema(query=Query, types=list(AbstractShareObject._implementers))
