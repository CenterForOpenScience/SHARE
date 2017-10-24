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
from api.sources.serializers import SourceSerializer
from api.sources.serializers import WritableSourceSerializer


logger = logging.getLogger(__name__)


class SourceViewSet(ShareViewSet, viewsets.ModelViewSet):
    filter_backends = (filters.OrderingFilter, )
    ordering = ('id', )
    ordering_fields = ('long_title', )
    permission_classes = (DjangoModelPermissionsOrAnonReadOnly, )

    queryset = Source.objects.none()  # Required for DjangoModelPermissions

    __conflicting_data = None

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return SourceSerializer
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
            self.__conflicting_data = serializer.data
            raise

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_renderer_context(self):
        context = super().get_renderer_context()
        if self.__conflicting_data is not None:
            context['conflicting_data'] = self.__conflicting_data
        return context
