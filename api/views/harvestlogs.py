from rest_framework import viewsets
from api.views import ShareObjectViewSet

from api.serializers import HarvestLogSerializer
from share.models import HarvestLog

class HarvestLogViewSet(ShareObjectViewSet):
    serializer_class = HarvestLogSerializer
    queryset = HarvestLog.objects.all()
