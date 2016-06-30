from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from api.filters import ChangeSetFilter
from api.serializers import NormalizedManuscriptSerializer, ChangeSetSerializer, ChangeSerializer, RawDataSerializer
from share.models import ChangeSet, Change
from share.tasks import MakeJsonPatches

__all__ = ('NormalizedManuscriptViewSet', 'ChangeSetViewSet', 'ChangeViewSet', 'RawDataViewSet')


class NormalizedManuscriptViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope, ]
    serializer_class = NormalizedManuscriptSerializer
    required_scopes = ['upload_normalized_manuscript', ]

    def get_queryset(self):
        return self.request.user.normalizedmanuscript_set.all()

    def create(self, request, *args, **kwargs):
        prelim_data = request.data
        prelim_data['source'] = request.user.id
        serializer = NormalizedManuscriptSerializer(data=prelim_data)
        if serializer.is_valid():
            nm_instance = serializer.save()
            async_result = MakeJsonPatches().delay(nm_instance.id, request.user.id)
            return Response({'normalized_id': nm_instance.id, 'task_id': async_result.id}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeSetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeSetSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = ChangeSet.objects.all()
    filter_class = ChangeSetFilter


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

    def get_queryset(self):
        return self.request.user.sharesource.rawdata_set.all()
