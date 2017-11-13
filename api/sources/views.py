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
from api.sources.serializers import (
    ReadonlySourceSerializer,
    CreateSourceSerializer,
    UpdateSourceSerializer,
)


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
        if self.request.method == 'POST':
            return CreateSourceSerializer
        return UpdateSourceSerializer

    def get_queryset(self):
        return Source.objects.exclude(icon='').exclude(is_deleted=True)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except exceptions.AlreadyExistsError as exc:
            return self._conflict_response(exc)

    def _conflict_response(self, exc):
        serializer = self.get_serializer(exc.existing_instance)
        return Response({
            'errors': [{
                'detail': exc.detail,
                'status': status.HTTP_409_CONFLICT,
            }],
            'data': serializer.data
        }, status=status.HTTP_409_CONFLICT)
