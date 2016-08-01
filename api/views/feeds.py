from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.core import serializers

import bleach
import dateparser
import json
import re
import requests

from share.models.creative import AbstractCreativeWork

RESULTS_PER_PAGE = 250

# TODO get elastic url from ENV/config
SEARCH_URL = 'http://localhost:8000/api/search/abstractcreativework/_search'

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
    title = 'SHARE RSS Feed'

    # TODO link to discover page? supposed to be html version of the feed, not
    # the feed itself
    link = '/rss/'

    description = 'Updates to the SHARE dataset'

    def get_object(self, request):
        elastic_query = request.GET.get('elasticQuery', {})
        query = elastic_query.get('query')
        filter = elastic_query.get('filter')

        from_ = request.GET.get('from', 0)

        elastic_data = {
            'sort': { 'date_created': 'desc' },
            'from': from_,
            'size': RESULTS_PER_PAGE
        }
        if query:
            elastic_data['query'] = query
        if filter:
            elastic_data['filter'] = filter
        return elastic_data

    def items(self, obj):
        headers = {'Content-Type': 'application/json'}
        elastic_response = requests.post(SEARCH_URL, data=json.dumps(obj), headers=headers)

        if elastic_response.status_code != 200:
            # TODO error response?
            return []

        def get_item(hit):
            source = hit.get('_source')
            source['@id'] = hit.get('_id')
            return source

        results = [get_item(hit) for hit in elastic_response.json()['hits']['hits']]
        # TODO anything else need to be done?
        return results

    def item_title(self, item):
        return sanitize_for_xml(item.get('title', 'No title provided.'))

    def item_description(self, item):
        return sanitize_for_xml(item.get('description', 'No description provided.'))

    def item_link(self, item):
        # TODO
        return 'http://localhost:8000/share/curate/{}/{}'.format(item.get('@type'), item.get('@id'))

    def item_pubdate(self, item):
        pubdate = item.get('date')
        return dateparser.parse(pubdate) if pubdate else None

    def item_updateddate(self, item):
        updateddate = item.get('date_updated')
        return dateparser.parse(updateddate) if updateddate else None

    def item_categories(self, item):
        subject = item.get('subject')
        tags = item.get('tags')
        categories = []
        if subject:
            categories.append(subject)
        if tags:
            categories.extend(tags)
        return [sanitize_for_xml(c) for c in categories]

class CreativeWorksAtom(CreativeWorksRSS):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description
