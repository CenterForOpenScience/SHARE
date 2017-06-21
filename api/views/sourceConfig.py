from rest_framework import viewsets
from api.views import ShareObjectViewSet
from rest_framework import filters
from api.serializers import SourceConfigSerializer
from share.models import SourceConfig
from api.pagination import FuzzyPageNumberPagination
from django.db.models import Count
from django.db.models import Aggregate
from share.models import HarvestLog
from django.db.models import OuterRef, Subquery
from django.db.models import IntegerField

class SourceConfigViewSet(ShareObjectViewSet):
    serializer_class = SourceConfigSerializer
    pagination_class = FuzzyPageNumberPagination
    queryset = SourceConfig.objects.all()

    
