from rest_framework import views
from rest_framework.response import Response

from share.models.validators import JSONLDValidator


__all__ = ('SchemaView',)


class SchemaView(views.APIView):
    def get(self, request, *args, **kwargs):
        schema = JSONLDValidator.jsonld_schema.schema
        return Response(schema)
