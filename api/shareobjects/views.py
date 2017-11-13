from rest_framework import viewsets

from api.base.views import ShareViewSet
from api.pagination import CursorPagination
from api.permissions import IsDeletedPremissions


class ShareObjectViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    pagination_class = CursorPagination
    permission_classes = (IsDeletedPremissions, )

    # Can't expose these until we have indexes added, both ascending and descending
    # filter_backends = (filters.OrderingFilter,)
    # ordering_fields = ('id', 'date_updated')

    # Override get_queryset to handle items marked as deleted.
    def get_queryset(self, list=True):
        queryset = super().get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs and hasattr(queryset.model, 'is_deleted'):
            return queryset.exclude(is_deleted=True)
        return queryset
