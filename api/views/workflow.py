from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from api.filters import ChangeSetFilterSet
from api.serializers import NormalizedDataSerializer, ChangeSetSerializer, ChangeSerializer, RawDataSerializer, \
    ShareUserSerializer
from share.models import ChangeSet, Change, RawData
from share.tasks import MakeJsonPatches

__all__ = ('NormalizedDataViewSet', 'ChangeSetViewSet', 'ChangeViewSet', 'RawDataViewSet', 'ShareUserViewSet')


class ShareUserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated,]
    serializer_class = ShareUserSerializer

    def get_queryset(self):
        return [self.request.user,]


class NormalizedDataViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope, ]
    serializer_class = NormalizedDataSerializer
    required_scopes = ['upload_normalized_manuscript', ]

    def get_queryset(self):
        return self.request.user.normalizeddata_set.all()

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
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeSetSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = ChangeSet.objects.all()
    filter_class = ChangeSetFilterSet


class ChangeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = Change.objects.all()


class RawDataViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope, ]
    serializer_class = RawDataSerializer
    required_scopes = ['upload_raw_data', ]

    queryset = RawData.objects.all()
