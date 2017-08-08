from rest_framework import viewsets
from rest_framework import filters
from api.views import ShareObjectViewSet
from share.util import IDObfuscator

from rest_framework import viewsets, views
# from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from api.serializers import HarvestLogSerializer
from share.models import HarvestLog
from api.views import ShareObjectViewSet


class SourceConfigFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        if 'source_config_id' in request.GET:
            decoded = IDObfuscator.decode_id(request.GET['source_config_id'])
            return queryset.filter(source_config_id=decoded)
        if 'status' in request.GET:
            return queryset.filter(status=request.GET['status'])

        else:
            return queryset

class HarvestLogViewSet(ShareObjectViewSet):
    queryset= HarvestLog.objects.all()
    serializer_class = HarvestLogSerializer
    filter_backends = (SourceConfigFilterBackend, )
    filter_fields = ['source_config__id', 'status',]
