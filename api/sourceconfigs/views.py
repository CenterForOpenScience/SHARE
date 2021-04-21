from rest_framework import viewsets

from api.sourceconfigs.serializers import SourceConfigSerializer
from api.base import ShareViewSet

from share.models import SourceConfig


class SourceConfigViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceConfigSerializer

    ordering = ('id', )

    def get_queryset(self):
        return SourceConfig.objects.all()
