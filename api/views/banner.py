from rest_framework import viewsets

from api.serializers import SiteBannerSerializer
from share.models import SiteBanner


class SiteBannerViewSet(viewsets.ReadOnlyModelViewSet):
    """View showing all active site-wide announcements."""
    serializer_class = SiteBannerSerializer

    ordering = ('id', )

    def get_queryset(self):
        return SiteBanner.objects.filter(active=True)
