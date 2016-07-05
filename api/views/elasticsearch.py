import requests
from rest_framework import views, permissions
from django.conf import settings
from furl import furl
from rest_framework.response import Response


class ElasticSearchView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def get(self, request, *args, **kwargs):
        es_url = furl('{}{}/search/'.format(
            settings.ELASTICSEARCH_URL,
            settings.ELASTICSEARCH_INDEX,
        )).add(query_params=request.query_params)
        resp = requests.get(es_url)
        return Response(data=resp.json(), headers={'Content-Type': 'application/json'})
