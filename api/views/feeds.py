from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.conf import settings
from django.core import serializers

import bleach
import dateparser
import json
import re
import requests

from share.models.creative import AbstractCreativeWork

RESULTS_PER_PAGE = 250

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                 chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                 chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)

def sanitize_for_xml(s):
    if s:
        s = RE_XML_ILLEGAL_COMPILED.sub('', s)
        return bleach.clean(s, strip=True, tags=[], attributes=[], styles=[])
    return s

class CreativeWorksRSS(Feed):
    link = '/'
    description = 'Updates to the SHARE open dataset'
    author_name = 'COS'

    def title(self, obj):
        query = json.dumps(obj.get('query', 'All'))
        return sanitize_for_xml('SHARE: Atom feed for query: {}'.format(query))

    def get_object(self, request):
        elastic_query = request.GET.get('elasticQuery')

        elastic_data = {
            'sort': { 'date_modified': 'desc' },
            'from': request.GET.get('from', 0),
            'size': RESULTS_PER_PAGE
        }
        if elastic_query:
            elastic_data['query'] = json.loads(elastic_query)
        return elastic_data

    def items(self, obj):
        headers = {'Content-Type': 'application/json'}
        search_url = '{}{}/abstractcreativework/_search'.format(settings.ELASTICSEARCH_URL, settings.ELASTICSEARCH_INDEX)
        elastic_response = requests.post(search_url, data=json.dumps(obj), headers=headers)
        json_response = elastic_response.json()

        if elastic_response.status_code != 200 or 'error' in json_response:
            return

        def get_item(hit):
            source = hit.get('_source')
            source['@id'] = hit.get('_id')
            return source

        return [get_item(hit) for hit in json_response['hits']['hits']]

    def item_title(self, item):
        return sanitize_for_xml(item.get('title', 'No title provided.'))

    def item_description(self, item):
        return sanitize_for_xml(item.get('description', 'No description provided.'))

    def item_link(self, item):
        # Link to SHARE curate page
        return '{}{}/curate/{}/{}'.format(settings.SHARE_API_URL, settings.EMBER_SHARE_PREFIX, item.get('@type'), item.get('@id'))

    def item_pubdate(self, item):
        pubdate = item.get('date')
        return dateparser.parse(pubdate) if pubdate else None

    def item_updateddate(self, item):
        updateddate = item.get('date_updated')
        return dateparser.parse(updateddate) if updateddate else None

    def item_categories(self, item):
        categories = [item.get('subject')]
        categories.extend(item.get('tags'))
        return [sanitize_for_xml(c) for c in categories if c]

class CreativeWorksAtom(CreativeWorksRSS):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description
