from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.core import serializers

import json
import requests

from share.models.creative import AbstractCreativeWork

RESULTS_PER_PAGE = 250

# TODO get elastic url from ENV/config
SHARE_URL = 'https://staging-share.osf.io/api/search/abstractcreativework/_search'

class CreativeWorksRSS(Feed):
    title = "SHARE RSS Feed"
    link = "/rss/"
    description = "Updates to the SHARE dataset"

    def get_object(self, request):
        elastic_query = request.GET.get('elasticQuery', {})
        page = request.GET.get('page', 1)

        return {
            'query': elastic_query.get('query'),
            'filter': elastic_query.get('filter'),
            'sort': { 'date_created': 'desc' },
            'start': (page - 1) * RESULTS_PER_PAGE,
            'size': RESULTS_PER_PAGE
        }

    def items(self, obj):
        # TODO headers?
        elastic_response = requests.post(SHARE_URL, data=obj)

        if elastic_response.status_code != 200:
            # TODO error response?
            return None

        results = elastic_response.json()['hits']['hits']


    def item_link(self, item):
        links = item.links.all()
        if links:
            return links[0].url
        else:
            return None

    def item_author_name(self, item):
        for contributor in item.contributors.all():
            return contributor.get_full_name()


class CreativeWorksAtom(CreativeWorksRSS):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description
