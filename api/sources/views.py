import logging

from rest_framework import filters
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from share.models import Source

from api.base import exceptions
from api.base import ShareViewSet
from api.sources.serializers import ReadonlySourceSerializer
from api.sources.serializers import WritableSourceSerializer


logger = logging.getLogger(__name__)


class SourceViewSet(ShareViewSet, viewsets.ModelViewSet):
    filter_backends = (filters.OrderingFilter, )
    ordering = ('id', )
    ordering_fields = ('long_title', )
    permission_classes = (DjangoModelPermissionsOrAnonReadOnly, )

    queryset = Source.objects.none()  # Required for DjangoModelPermissions

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ReadonlySourceSerializer
        return WritableSourceSerializer

    def get_queryset(self):
        return Source.objects.exclude(icon='').exclude(is_deleted=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except exceptions.AlreadyExistsError as e:
            serializer = self.get_serializer(e.existing_instance)
            return Response({
                'errors': [{
                    'detail': e.detail,
                    'status': status.HTTP_409_CONFLICT,
                }],
                'data': serializer.data
            }, status=status.HTTP_409_CONFLICT)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
