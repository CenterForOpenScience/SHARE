from rest_framework import viewsets
from rest_framework import filters
from django_filters.filters import MultipleChoiceFilter
from api.views import ShareObjectViewSet
from share.util import IDObfuscator

from api.serializers import HarvestLogSerializer
from share.models import HarvestLog

class SourceConfigFilterBackend(MultipleChoiceFilter):
    def filter_queryset(self, request, queryset, view, conjoined=True):
        if 'source_config_id' in request.GET:
            decoded = IDObfuscator.decode_id(request.GET['source_config_id'])
            queryset = queryset.filter(source_config_id=decoded)
        if 'status' in request.GET:
            queryset = queryset.filter(status__in=request.GET.getlist('status'))
        return queryset
        #return queryset.order_by('endDate')

class HarvestLogViewSet(ShareObjectViewSet):
    serializer_class = HarvestLogSerializer
    queryset = HarvestLog.objects.all()
    filter_backends = (SourceConfigFilterBackend, )
    filter_fields = ('status',)
