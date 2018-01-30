
from xml.sax.saxutils import unescape
import datetime
import json
import logging
import re
import requests

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.conf import settings


logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 250

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
    (
        chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
        chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
        chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff)
    )

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)


def prepare_string(s):
    if s:
        s = RE_XML_ILLEGAL_COMPILED.sub('', s)
        # Strings will be autoescaped during XML generation, and data from elasticsearch
        # is already bleached. Unescape to escape extra escapes.
        return unescape(s)
    return s


def parse_date(s):
    if not s:
        return None

    # strptime can't parse +00:00
    s = re.sub(r'\+(\d\d):(\d\d)', r'+\1\2', s)

    for date_fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z'):
        try:
            return datetime.datetime.strptime(s, date_fmt)
        except ValueError:
            pass
    logger.error('Could not parse date "%s"', s)
    return None


class CreativeWorksRSS(Feed):
    link = '{}api/v2/rss/'.format(settings.SHARE_WEB_URL)
    description = 'Updates to the SHARE open dataset'
    author_name = 'SHARE'

    def title(self, obj):
        query = json.dumps(obj.get('query', 'All'))
        return prepare_string('SHARE: Atom feed for query: {}'.format(query))

    def get_object(self, request):
        self._order = request.GET.get('order')
        elastic_query = request.GET.get('elasticQuery')

        if self._order not in {'date_modified', 'date_updated'}:
            self._order = 'date_modified'

        elastic_data = {
            'sort': {self._order: 'desc'},
            'from': request.GET.get('from', 0),
            'size': RESULTS_PER_PAGE
        }

        if elastic_query:
            try:
                elastic_data['query'] = json.loads(elastic_query)
            except ValueError:
                pass  # Don't die on malformed JSON

        return elastic_data

    def items(self, obj):
        headers = {'Content-Type': 'application/json'}
        search_url = '{}{}/creativeworks/_search'.format(settings.ELASTICSEARCH_URL, settings.ELASTICSEARCH_INDEX)
        elastic_response = requests.post(search_url, data=json.dumps(obj), headers=headers)
        json_response = elastic_response.json()

        if elastic_response.status_code != 200 or 'error' in json_response:
            return

        def get_item(hit):
            source = hit.get('_source')
            source['id'] = hit.get('_id')
            return source

        return [get_item(hit) for hit in json_response['hits']['hits']]

    def item_title(self, item):
        return prepare_string(item.get('title', 'No title provided.'))

    def item_description(self, item):
        return prepare_string(item.get('description', 'No description provided.'))

    def item_link(self, item):
        # Link to SHARE curate page
        return '{}{}/{}'.format(settings.SHARE_WEB_URL, item.get('type').replace(' ', ''), item.get('id'))

    def item_author_name(self, item):
        contributor_list = item.get('lists', []).get('contributors', [])
        creators = [c for c in contributor_list if 'order_cited' in c]

        authors = sorted(
            creators,
            key=lambda x: x['order_cited'],
            reverse=False
        ) if creators else contributor_list

        if not authors:
            return 'No authors provided.'
        author_name = authors[0]['name'] or authors[0]['cited_as']
        return prepare_string('{}{}'.format(author_name, ' et al.' if len(authors) > 1 else ''))

    def item_pubdate(self, item):
        return parse_date(item.get('date_published'))

    def item_updateddate(self, item):
        return parse_date(item.get(self._order))

    def item_categories(self, item):
        categories = item.get('subjects', [])
        categories.extend(item.get('tags', []))
        return [prepare_string(c) for c in categories if c]


class CreativeWorksAtom(CreativeWorksRSS):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description
    link = '{}api/v2/atom/'.format(settings.SHARE_WEB_URL)
