from rest_framework import viewsets, views
# from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from api.serializers import HarvestLogSerializer
from share.models import HarvestLog
from api.views import ShareObjectViewSet

class HarvestLogViewSet(ShareObjectViewSet):
    queryset= HarvestLog.objects.all()
    serializer_class = HarvestLogSerializer

    filter_backends = (DjangoFilterBackend, )
    filter_fields = ['source_config__id',]

    # def get_queryset(self):
    #     import ipdb; ipdb.set_trace()
