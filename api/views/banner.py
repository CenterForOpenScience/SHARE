from rest_framework import viewsets
from rest_framework_json_api.pagination import PageNumberPagination

from api.serializers import SiteBannerSerializer
from share.models import SiteBanner


class SiteBannerViewSet(viewsets.ReadOnlyModelViewSet):
    """View showing all active site-wide announcements."""
    serializer_class = SiteBannerSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return SiteBanner.objects.filter(active=True)
