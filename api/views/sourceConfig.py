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

    # def get_queryset(self):
    #     recent_harvests = HarvestLog.objects.filter(
    #         source_config_id = OuterRef(OuterRef('id')),
    #         status__in = [HarvestLog.STATUS.failed, HarvestLog.STATUS.succeeded]
    #         ).order_by('-date_started')[:10]
    #     recent_fails = HarvestLog.objects.filter(
    #         status = HarvestLog.STATUS.failed,
    #         id__in = Subquery(recent_harvests.values('id')),
    #         # output_field = models.IntegerField())
    #         )
    #     queryset = SourceConfig.objects.all().annotate(
    #         fails=Count(Subquery(recent_fails.values('id')),
    #         # output_field = models.IntegerField()))
    #         )
    #     queryset = queryset.order_by('fails')
    #     return queryset
