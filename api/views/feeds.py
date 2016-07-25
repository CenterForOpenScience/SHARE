from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.core import serializers

import requests

from share.models.creative import AbstractCreativeWork


SHARE_URL = 'https://staging-share.osf.io/api/search/abstractcreativework/_search'

class CreativeWorksRSS(Feed):
    title = "SHARE RSS Feed"
    link = "/rss/"
    description = "Updates to the SHARE dataset"

    def items(self):
        # TODO - make this filterable and probably not use only AbstractCreativeWorks
        # TODO - make use elasticsearch results?
        return AbstractCreativeWork.objects.order_by('-date_updated')[:5]

    def item_link(self, item):
        links = item.links.all()
        if links:
            return links[0].url
        else:
            return None

    def item_author_name(self, item):
        for contributor in item.contributors.all():
            return contributor.get_full_name()

import re
import pytz
import requests
import json
from urllib.parse import parse_qs
from werkzeug.contrib.atom import AtomFeed

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)

class CreativeWorksAtom(Feed):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description
    items = []


    def item_link(self, *args, **kwargs):
        return self.url

    def get_object(self, request, *args, **kwargs):
        query_params = parse_qs(request.get_full_path().replace(request.path + '?', ''))
        data = query_params['jsonQuery'][0] if query_params and query_params['jsonQuery'] else {}
        params = json.loads(query_params['urlQuery'][0] if query_params and query_params['urlQuery'] else {})
        if data == 'undefined':
            data = False
        else:
            data = json.loads(data)
        headers = {'Content-Type': 'application/json'}
        url = 'https://staging-share.osf.io/api/search/abstractcreativework/_search'
        r = requests.post(url, headers=headers, params=params, data=data) if params and data else (
            requests.post(url, headers=headers, params=params) if params else (
                requests.post(url, headers=headers, data=data) if data else requests.post(url, headers=headers)
            )
        )
        self.link = '/atom/'
        self.url = 'https://cos.io/share'
        data = r.json()
        start = 1
        size = 10
        if params and params.get('q') == '*':
            title_query = 'All'
        else:
            title_query = params.get('q') if params else 'None'

        self.title = 'SHARE: Atom Feed for query: "{title_query}"'.format(title_query=title_query)
        self.author = 'COS'

        links = [
            {'href': '{url}?page=1'.format(url=url), 'rel': 'first'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size) + 2), 'rel': 'next'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size)), 'rel': 'previous'}
        ]

        self.links = links[1:-1] if (start / size) == 0 else links

        self.items.append(to_atom(data['hits']['hits'][0]))
        for doc in data['hits']['hits']:
            try:
                pass#self.items.append(to_atom(doc))
            except ValueError as e:
                # panic
                pass


def to_atom(result):
    result = result.get('_source')
    return {
            'title': html_and_illegal_unicode_replace(result.get('title')) or 'No title provided.',
            'summary': html_and_illegal_unicode_replace(result.get('description')) or 'No summary provided.',
            #'id': result['uris']['canonicalUri'],
            #'updated': get_date_updated(result),
            'links': [
                #{'href': result['uris']['canonicalUri'], 'rel': 'alternate'}
            ],
            'author': format_contributors_for_atom(result['contributors']),
            'categories': [{'term': html_and_illegal_unicode_replace(tag)} for tag in (result.get('tags', []) + result.get('subjects', []))],
            #'published': parse(result.get('providerUpdatedDateTime'))
        }

def html_and_illegal_unicode_replace(atom_element):
    """ Replace an illegal for XML unicode character with nothing.
    This fix thanks to Matt Harper from his blog post:
    https://maxharp3r.wordpress.com/2008/05/15/pythons-minidom-xml-and-illegal-unicode-characters/
    """
    if atom_element:
        new_element = RE_XML_ILLEGAL_COMPILED.sub('', atom_element)
        return strip_html(new_element)
    return atom_element

def format_contributors_for_atom(contributors_list):
    return [
        {
            'name': html_and_illegal_unicode_replace(entry['name'])
        } for entry in contributors_list
    ]

from dateutil.parser import parse

def get_date_updated(result):
    try:
        updated = pytz.utc.localize(parse(result.get('providerUpdatedDateTime')))
    except ValueError:
        updated = parse(result.get('providerUpdatedDateTime'))

    return updated

import collections
import bleach


def strip_html(unclean):
    """Sanitize a string, removing (as opposed to escaping) HTML tags

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    # We make this noop for non-string, non-collection inputs so this function can be used with higher-order
    # functions, such as rapply (recursively applies a function to collections)
    if not isinstance(unclean, str) and not is_iterable(unclean) and unclean is not None:
        return unclean
    return bleach.clean(unclean, strip=True, tags=[], attributes=[], styles=[])

def is_iterable(obj):
    return isinstance(obj, collections.Iterable)
