from rest_framework import viewsets
from api.views import ShareObjectViewSet

# trying to fix shit
from api.serializers import SourceConfigSerializer
from share.models import SourceConfig

class SourceConfigViewSet(ShareObjectViewSet):
    serializer_class = SourceConfigSerializer
    queryset= SourceConfig.objects.all()
