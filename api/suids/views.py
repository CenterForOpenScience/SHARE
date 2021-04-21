from rest_framework import viewsets

from api.suids.serializers import SuidSerializer
from api.base import ShareViewSet

from share.models import SourceUniqueIdentifier


class SuidViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = SuidSerializer

    ordering = ('id', )

    def get_queryset(self):
        return SourceUniqueIdentifier.objects.all()
