from rest_framework import viewsets
from api.views import ShareObjectViewSet
from api.serializers import SourceConfigSerializer
from share.models import SourceConfig
from api.pagination import FuzzyPageNumberPagination

class SourceConfigViewSet(ShareObjectViewSet):
    serializer_class = SourceConfigSerializer
    queryset= SourceConfig.objects.all()
    pagination_class = FuzzyPageNumberPagination
