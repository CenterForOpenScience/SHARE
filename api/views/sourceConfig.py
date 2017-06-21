from rest_framework import viewsets, views
from api.serializers import SourceConfigSerializer
from share.models import SourceConfig
from rest_framework import filters
import django_filters.rest_framework
from api.views import ShareObjectViewSet


class SourceConfigViewSet(ShareObjectViewSet):
    queryset= SourceConfig.objects.all()
    serializer_class = SourceConfigSerializer
    filter_backends = (filters.SearchFilter, )
    search_fields = ['label','base_url']
