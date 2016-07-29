import re
import pytz
import requests
import json
import bleach
from urllib.parse import parse_qs
from dateutil.parser import parse

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed


SHARE_URL = 'https://staging-share.osf.io/api/search/abstractcreativework/_search'

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)


class Atom1CustomFeed(Atom1Feed):
    def add_item_elements(self, handler, item):
        super(Atom1CustomFeed, self).add_item_elements(handler, item)
        for author in item.get('authors'):
            handler.startElement('author', {})
            handler.addQuickElement('name', author)
            handler.endElement('author')

class CreativeWorksAtom(Feed):
    feed_type = Atom1CustomFeed
    items = []
    link = '/atom/'
    url = 'https://cos.io/share'  # needs to be changed to correct url
    author_name = 'COS'

    def item_link(self, item):
        return item.get('links')[0]['href'] if item.get('links') else self.url

    def item_id(self, item):
        return item.get('id')

    def item_categories(self, item):
        return item.get('categories')

    def item_title(self, item):
        return item.get('title')

    def item_description(self, item):
        return item.get('description')

    def item_updateddate(self, item):
        return item.get('updated')

    def item_pubdate(self, item):
        return item.get('published')

    def item_extra_kwargs(self, item):
        return {'authors': item.get('authors')}

    def get_object(self, request):
        query_params = parse_qs(request.get_full_path().replace(request.path + '?', ''))
        request_kwargs = {}
        params = {}
        start = 1
        size = 10

        if query_params:
            if query_params.get('jsonQuery'):
                request_kwargs['data'] = query_params['jsonQuery'][0]
            if query_params.get('urlQuery'):
                params = json.loads(query_params['urlQuery'][0])
                request_kwargs['params'] = params
            if query_params.get('page'):
                start = query_params.get('page')
                params['from'] = start*size


        headers = {'Content-Type': 'application/json'}
        url = SHARE_URL
        r = requests.post(url, headers=headers, **request_kwargs)

        data = r.json()

        if r.status_code != 200:
            return

        title_query = 'All' if params.get('q') == '*' else params.get('q')

        self.title = 'SHARE: Atom Feed for query: "{}"'.format(title_query or 'None')

        links = [
            {'href': '{url}?page=1'.format(url=url), 'rel': 'first'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size) + 2), 'rel': 'next'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size)), 'rel': 'previous'}
        ]

        self.links = links[1:-1] if (start / size) == 0 else links

        for doc in data['hits']['hits']:
            try:
                result = doc.get('_source')
                self.items.append({
                    'title': html_and_illegal_unicode_replace(result.get('title')) or 'No title provided.',
                    'description': html_and_illegal_unicode_replace(result.get('description')) or 'No summary provided.',
                    'id': result['links'][0] if result.get('links') and len(result['links']) else 'No identifying link provided',
                    'updated': get_date_updated(result),
                    'links': [{'href': link, 'rel': 'alternate'} for link in result.get('links')],
                    'authors': [html_and_illegal_unicode_replace(entry['full_name']) for entry in result.get('contributors')],
                    'categories': [html_and_illegal_unicode_replace(tag) for tag in (result.get('tags', []) + result.get('subjects', []))],
                    'published': parse(result.get('date_updated')) if result.get('date_updated') else parse(result.get('date_created'))
                })
            except ValueError as e:
                # panic
                pass

def html_and_illegal_unicode_replace(atom_element):
    """ Replace an illegal for XML unicode character with nothing.
    This fix thanks to Matt Harper from his blog post:
    https://maxharp3r.wordpress.com/2008/05/15/pythons-minidom-xml-and-illegal-unicode-characters/
    """
    if atom_element:
        new_element = RE_XML_ILLEGAL_COMPILED.sub('', atom_element)
        return bleach.clean(new_element, strip=True, tags=[], attributes=[], styles=[]) if isinstance(new_element, str) else None
    return atom_element

def get_date_updated(result):
    updated = None
    if result.get('date_updated'):
        try:
            updated = pytz.utc.localize(parse(result.get('date_updated')))
        except ValueError:
            updated = parse(result.get('date_updated'))
    return updated
