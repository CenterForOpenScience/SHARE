import json

from rest_framework import viewsets, views, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from django import http
from django.views.generic.base import RedirectView

from api.filters import ShareObjectFilterSet
from share import serializers
from api import serializers as api_serializers


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
            data = [change.change_set.normalized_data.raw for change in changes]

        page = self.paginate_queryset(data)
        if page is not None:
            ser = api_serializers.RawDataSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(ser.data)
        ser = api_serializers.RawDataSerializer(data, many=True, context={'request': request})
        return Response(ser.data)


class RelationsViewSet(viewsets.ReadOnlyModelViewSet):
    @detail_route(methods=['get'])
    def relations(self, request, pk=None):
        if pk is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        obj = self.get_object()
        relations = obj.outgoing_relations.all() | obj.incoming_relations.all()
        page = self.paginate_queryset(relations)
        if page is not None:
            ser = serializers.RelationSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(ser.data)
        ser = serializers.RelationSerializer(relations, many=True, context={'request': request})
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


class CreativeWorkIdentifierViewSet(ShareObjectViewSet):
    serializer_class = serializers.CreativeWorkIdentifierSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class PersonIdentifierViewSet(ShareObjectViewSet):
    serializer_class = serializers.PersonIdentifierSerializer
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


class RelationViewSet(ShareObjectViewSet):
    serializer_class = serializers.RelationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'extra'
    )


class RelationTypesView(views.APIView):
    with open('./share/models/relation-types.json') as fobj:
        RELATION_TYPES = json.load(fobj)

    def get(self, request, *args, **kwargs):
        return Response(self.RELATION_TYPES)


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.SubjectSerializer
    queryset = serializer_class.Meta.model.objects.all()


class ShareUserView(views.APIView):
    def get(self, request, *args, **kwargs):
        ser = api_serializers.ShareUserSerializer(request.user, token=True)
        return Response(ser.data)


class HttpSmartResponseRedirect(http.HttpResponseRedirect):
    status_code = 307


class HttpSmartResponsePermanentRedirect(http.HttpResponsePermanentRedirect):
    status_code = 308


class APIVersionRedirectView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return '/api/v2/{}'.format(kwargs['path'])

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)
        if url:
            if self.permanent:
                return HttpSmartResponsePermanentRedirect(url)
            return HttpSmartResponseRedirect(url)
        return http.HttpResponseGone()


def make_creative_work_view_set_class(model):
    class CreativeWorkViewSet(RelationsViewSet, ShareObjectViewSet):
        serializer_class = serializers.make_creative_work_serializer_class(model)
        queryset = serializer_class.Meta.model.objects.all().select_related('extra')
    return CreativeWorkViewSet
