from rest_framework import viewsets, views, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from rest_framework_json_api import serializers

from django import http
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.generic.base import RedirectView
from django.shortcuts import get_object_or_404

from api.filters import ShareObjectFilterSet
from api import serializers as api_serializers

from share.util import IDObfuscator, InvalidID
from share.models import ShareUser


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


class ShareObjectViewSet(ChangesViewSet, VersionsViewSet, RawDataDetailViewSet, viewsets.ReadOnlyModelViewSet):
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    filter_class = ShareObjectFilterSet

    # override to convert encoded pk to an actual pk
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        try:
            (model, decoded_pk) = IDObfuscator.decode(self.kwargs[lookup_url_kwarg])
            concrete_model = self.serializer_class.Meta.model._meta.concrete_model
            if model is not concrete_model:
                raise serializers.ValidationError('The specified ID refers to an {}. Expected {}'.format(model._meta.model_name, concrete_model._meta.model_name))
        except InvalidID:
            raise serializers.ValidationError('Invalid ID')

        filter_kwargs = {self.lookup_field: decoded_pk}
        obj = get_object_or_404(queryset, **filter_kwargs)
        if obj.same_as_id:
            obj = obj._meta.concrete_model.objects.get_canonical(obj.id)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


# Other

class ShareUserView(views.APIView):
    def get(self, request, *args, **kwargs):
        ser = api_serializers.ShareUserSerializer(request.user, token=True)
        return Response(ser.data)


@require_GET
def source_icon_view(request, source_name):
    source = get_object_or_404(Source, name=source_name)
    if not source.favicon:
        raise http.Http404('Favicon for source {} does not exist'.format(source_name))
    response = http.FileResponse(source.icon)
    response['Content-Type'] = 'image/x-icon'
    return response


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


class ServerStatusView(views.APIView):
    def get(self, request):
        return Response({
            'id': '1',
            'type': 'Status',
            'attributes': {
                'status': 'up',
                'version': settings.VERSION,
            }
        })
