from xml.sax.saxutils import unescape
import json
import logging

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.conf import settings
import sentry_sdk

from share.search import index_strategy
from share.search.exceptions import IndexStrategyError
from share.util.xml import strip_illegal_xml_chars
from share.util.fromisoformat import fromisoformat


logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 250


def prepare_string(s):
    if s:
        s = strip_illegal_xml_chars(s)
        # Strings will be autoescaped during XML generation, and data from elasticsearch
        # is already bleached. Unescape to escape extra escapes.
        return unescape(s)
    return s


class MetadataRecordsRSS(Feed):
    link = '{}api/v2/feeds/rss/'.format(settings.SHARE_WEB_URL)
    description = 'Updates to the SHARE open dataset'
    author_name = 'SHARE'

    _search_strategy: index_strategy.IndexStrategy

    def title(self, obj):
        query = json.dumps(obj.get('query', 'All'))
        return prepare_string('SHARE: Atom feed for query: {}'.format(query))

    def get_object(self, request):
        self._order = request.GET.get('order')
        elastic_query = request.GET.get('elasticQuery')
        self._search_strategy = index_strategy.get_strategy_for_sharev2_search(request.GET.get('indexStrategy'))

        if self._order not in {'date_modified', 'date_updated', 'date_created', 'date_published'}:
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
        try:
            json_response = self._search_strategy.pls_handle_search__passthru(
                request_body=obj,
            )
        except IndexStrategyError:
            sentry_sdk.capture_exception()
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
        def _sort_key(identifier: str):
            # choose the shortest by length, breaking ties with unicode sort order
            return (len(identifier), identifier)
        return min(
            item.get('identifiers', ()),
            default='',
            key=_sort_key,
        )

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
        return fromisoformat(item.get('date_published') or item.get('date_created'))

    def item_updateddate(self, item):
        return fromisoformat(item.get(self._order))

    def item_categories(self, item):
        categories = item.get('subjects', [])
        categories.extend(item.get('tags', []))
        return [prepare_string(c) for c in categories if c]


class MetadataRecordsAtom(MetadataRecordsRSS):
    feed_type = Atom1Feed
    subtitle = MetadataRecordsRSS.description
    link = '{}api/v2/feeds/atom/'.format(settings.SHARE_WEB_URL)
