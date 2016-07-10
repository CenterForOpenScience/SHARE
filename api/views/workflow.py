from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from api.filters import ChangeSetFilterSet, ChangeFilterSet
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.serializers import NormalizedDataSerializer, ChangeSetSerializer, ChangeSerializer, RawDataSerializer, \
    ShareUserSerializer, ProviderSerializer
from share.models import ChangeSet, Change, RawData, ShareUser, NormalizedData
from share.tasks import MakeJsonPatches

__all__ = ('NormalizedDataViewSet', 'ChangeSetViewSet', 'ChangeViewSet', 'RawDataViewSet', 'ShareUserViewSet', 'ProviderViewSet')


class ShareUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShareUserSerializer

    def get_queryset(self):
        return [self.request.user,]


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderSerializer

    def get_queryset(self):
        return ShareUser.objects.exclude(robot='')


class NormalizedDataViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrTokenHasScopeOrIsAuthenticated, ]
    serializer_class = NormalizedDataSerializer
    required_scopes = ['upload_normalized_manuscript', ]

    def get_queryset(self):
        return NormalizedData.objects.all()

    def create(self, request, *args, **kwargs):
        prelim_data = request.data
        prelim_data['source'] = request.user.id
        serializer = NormalizedDataSerializer(data=prelim_data)
        if serializer.is_valid():
            nm_instance = serializer.save()
            async_result = MakeJsonPatches().delay(nm_instance.id, request.user.id)
            return Response({'normalized_id': nm_instance.id, 'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeSetViewSet(viewsets.ModelViewSet):
    serializer_class = ChangeSetSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]

    def get_queryset(self):
        return ChangeSet.objects.all().select_related('normalized_data__source')
    filter_class = ChangeSetFilterSet


class ChangeViewSet(viewsets.ModelViewSet):
    serializer_class = ChangeSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = Change.objects.all()
    filter_class = ChangeFilterSet


class RawDataViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RawDataSerializer

    queryset = RawData.objects.all()
