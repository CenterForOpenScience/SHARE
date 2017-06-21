from rest_framework import viewsets
from rest_framework import filters
from api.views import ShareObjectViewSet
from share.util import IDObfuscator

from api.serializers import HarvestLogSerializer
from share.models import HarvestLog


class SourceConfigFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        if 'source_config_id' in request.GET:
            decoded = IDObfuscator.decode_id(request.GET['source_config_id'])
            return queryset.filter(source_config_id=decoded)
        else:
            return queryset

class HarvestLogViewSet(ShareObjectViewSet):
    serializer_class = HarvestLogSerializer
    queryset = HarvestLog.objects.all()
    filter_backends = (SourceConfigFilterBackend, )
