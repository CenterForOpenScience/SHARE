from rest_framework import viewsets

from api.serializers import SourceConfigSerializer
from share.models import SourceConfig

class SourceConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceConfigSerializer

    def get_queryset(self):
        return SourceConfig.objects.all()
