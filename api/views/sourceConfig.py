from rest_framework import viewsets
from api.views import ShareObjectViewSet
from rest_framework import filters
from api.serializers import SourceConfigSerializer
from share.models import SourceConfig
from api.pagination import FuzzyPageNumberPagination

class SourceConfigViewSet(ShareObjectViewSet):
    serializer_class = SourceConfigSerializer
    queryset= SourceConfig.objects.all().order_by('harvest_logs__status')
    pagination_class = FuzzyPageNumberPagination
    for i in queryset:
        print(i)
        print("harvest logs:", i.harvest_logs)
