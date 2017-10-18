import logging

from rest_framework import filters
from rest_framework import viewsets
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.permissions import SAFE_METHODS

from share.models import Source

from api.base import ShareViewSet
from api.sources.serializers import SourceSerializer
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
            return SourceSerializer
        return WritableSourceSerializer

    def get_queryset(self):
        return Source.objects.exclude(icon='').exclude(is_deleted=True)
