import re
import pytz
import requests
import json

from werkzeug.contrib.atom import AtomFeed

from rest_framework import viewsets, permissions, views, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from api.filters import ShareObjectFilterSet
from share import serializers
from api import serializers as api_serializers

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)

class VersionsViewSet(viewsets.ReadOnlyModelViewSet):
    @detail_route(methods=['get'])
    def versions(self, request, pk=None):
        if pk is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        versions = self.get_object().versions.all()
        page = self.paginate_queryset(versions)
        if page is not None:
            ser = self.get_serializer(page, many=True, version_serializer=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(versions, many=True, version_serializer=True)
        return Response(ser.data)


class ChangesViewSet(viewsets.ReadOnlyModelViewSet):
    @detail_route(methods=['get'])
    def changes(self, request, pk=None):
        if pk is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        changes = self.get_object().changes.all()
        page = self.paginate_queryset(changes)
        if page is not None:
            ser = api_serializers.ChangeSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(ser.data)
        ser = api_serializers.ChangeSerializer(changes, many=True, context={'request': request})
        return Response(ser.data)


class RawDataDetailViewSet(viewsets.ReadOnlyModelViewSet):
    @detail_route(methods=['get'])
    def rawdata(self, request, pk=None):
        if pk is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        data = []
        obj = self.get_object()
        if not obj.changes.exists():
            data.append(obj.change.change_set.normalized_data.raw)
        else:
            changes = obj.changes.all()
            data = [change.changeset.normalized_data.raw for change in changes]

        page = self.paginate_queryset(data)
        if page is not None:
            ser = api_serializers.RawDataSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(ser.data)
        ser = api_serializers.RawDataSerializer(data, many=True, context={'request': request})
        return Response(ser.data)



class ShareObjectViewSet(ChangesViewSet, VersionsViewSet, RawDataDetailViewSet, viewsets.ReadOnlyModelViewSet):
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    filter_class = ShareObjectFilterSet


class ExtraDataViewSet(ShareObjectViewSet):
    serializer_class = serializers.ExtraDataSerializer
    queryset = serializer_class.Meta.model.objects.all()
    filter_class = None


class EntityViewSet(ShareObjectViewSet):
    serializer_class = serializers.EntitySerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class VenueViewSet(ShareObjectViewSet):
    serializer_class = serializers.VenueSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class OrganizationViewSet(ShareObjectViewSet):
    serializer_class = serializers.OrganizationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class PublisherViewSet(ShareObjectViewSet):
    serializer_class = serializers.PublisherSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class InstitutionViewSet(ShareObjectViewSet):
    serializer_class = serializers.InstitutionSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class IdentifierViewSet(ShareObjectViewSet):
    serializer_class = serializers.IdentifierSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class PersonViewSet(ShareObjectViewSet):
    serializer_class = serializers.PersonSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'extra'
    ).prefetch_related(
        'emails',
        'affiliations',
        'identifiers'
    )


class AffiliationViewSet(ShareObjectViewSet):
    serializer_class = serializers.AffiliationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra', 'person', 'entity')


class ContributorViewSet(ShareObjectViewSet):
    serializer_class = serializers.ContributorSerializer
    queryset = serializer_class.Meta.model.objects.select_related('extra', 'person', 'creative_work')


class FunderViewSet(ShareObjectViewSet):
    serializer_class = serializers.FunderSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class AwardViewSet(ShareObjectViewSet):
    serializer_class = serializers.AwardSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class TagViewSet(ShareObjectViewSet):
    serializer_class = serializers.TagSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class LinkViewSet(ShareObjectViewSet):
    serializer_class = serializers.LinkSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class CreativeWorkViewSet(ShareObjectViewSet):
    serializer_class = serializers.CreativeWorkSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )




class PreprintViewSet(ShareObjectViewSet):
    serializer_class = serializers.PreprintSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )


class PublicationViewSet(ShareObjectViewSet):
    serializer_class = serializers.PublicationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )


class ProjectViewSet(ShareObjectViewSet):
    serializer_class = serializers.ProjectSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )


class ManuscriptViewSet(ShareObjectViewSet):
    serializer_class = serializers.ManuscriptSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )

class ShareUserView(views.APIView):
    def get(self, request, *args, **kwargs):
        ser = api_serializers.ShareUserSerializer(request.user, token=True)
        return Response(ser.data)


class AtomFeedView(views.APIView):
    serializer_class = api_serializers.AtomFeedSerializer
    def get(self, request, **kwargs):
        query_params = request.query_params
        data = query_params['jsonQuery'] if query_params else {}
        params = json.loads(query_params['urlQuery'] if query_params else {})
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
        url = 'https://cos.io/share'
        data = r.json()
        start = 1
        size = 10
        if params and params.get('q') == '*':
            title_query = 'All'
        else:
            title_query = params.get('q') if params else 'None'

        title = 'SHARE: Atom Feed for query: "{title_query}"'.format(title_query=title_query)
        author = 'COS'

        links = [
            {'href': '{url}?page=1'.format(url=url), 'rel': 'first'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size) + 2), 'rel': 'next'},
            {'href': '{url}?page={page}'.format(url=url, page=(start / size)), 'rel': 'previous'}
        ]

        links = links[1:-1] if (start / size) == 0 else links

        feed = AtomFeed(
            title=title,
            feed_url=url,
            author=author,
            links=links
        )

        for doc in data['hits']['hits']:
            try:
                feed.add(**to_atom(doc))
            except ValueError as e:
                # panic
                pass
        return CreativeWorksAtom()

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

