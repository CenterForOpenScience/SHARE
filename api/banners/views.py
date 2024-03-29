from rest_framework import viewsets

from api.banners.serializers import SiteBannerSerializer
from api.base import ShareViewSet
from api.pagination import CursorPagination

from share.models import SiteBanner


class SiteBannerViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    """View showing all active site-wide announcements."""
    pagination_class = CursorPagination
    serializer_class = SiteBannerSerializer

    ordering = ('id', )

    def get_queryset(self):
        return SiteBanner.objects.filter(active=True).order_by(*self.ordering)
