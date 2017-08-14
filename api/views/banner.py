from rest_framework import viewsets

from api.serializers import SiteBannerSerializer
from share.models import SiteBanner
from api.base import ShareViewSet


class SiteBannerViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    """View showing all active site-wide announcements."""
    serializer_class = SiteBannerSerializer

    ordering = ('id', )

    def get_queryset(self):
        return SiteBanner.objects.filter(active=True)
