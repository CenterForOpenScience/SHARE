from rest_framework import viewsets

from api.serializers import HarvestLogSerializer
from share.models import HarvestLog

class HarvestLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HarvestLogSerializer

    def get_queryset(self):
        return HarvestLog.objects.all()
