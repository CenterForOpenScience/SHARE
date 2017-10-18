from api.serializers import SourceConfigSerializer, HarvesterSerializer, TransformerSerializer
from api.views.share import ShareObjectViewSet
from api.pagination import FuzzyPageNumberPagination

from share.models import SourceConfig, Harvester, Transformer


class SourceConfigViewSet(ShareObjectViewSet):
    pagination_class = FuzzyPageNumberPagination
    serializer_class = SourceConfigSerializer
    queryset = SourceConfig.objects.all()


class HarvesterViewSet(ShareObjectViewSet):
    pagination_class = FuzzyPageNumberPagination
    serializer_class = HarvesterSerializer
    queryset = Harvester.objects.all()


class TransformerViewSet(ShareObjectViewSet):
    pagination_class = FuzzyPageNumberPagination
    serializer_class = TransformerSerializer
    queryset = Transformer.objects.all()
