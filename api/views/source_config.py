from share.models import SourceConfig

from api.pagination import FuzzyPageNumberPagination
from api.serializers import SourceConfigSerializer
from api.views import ShareObjectViewSet


class SourceConfigViewSet(ShareObjectViewSet):
    serializer_class = SourceConfigSerializer
    pagination_class = FuzzyPageNumberPagination
    queryset = SourceConfig.objects.all()
