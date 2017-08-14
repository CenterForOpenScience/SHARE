from rest_framework import viewsets
from rest_framework_json_api import serializers

from share.util import IDObfuscator, InvalidID

from api.pagination import CursorPagination
from api.permissions import IsDeletedPremissions


__all__ = ('ShareViewSet', 'ShareObjectViewSet', )


class ShareViewSet(viewsets.ModelViewSet):
    ordering = ('-id', )

    def initial(self, request, *args, **kwargs):
        ret = super().initial(request, *args, **kwargs)

        lookup_key = self.lookup_url_kwarg or self.lookup_field
        if lookup_key not in self.kwargs:
            return ret

        # Decode id's before the all the internal dispatching
        try:
            model, id = IDObfuscator().decode(self.kwargs[lookup_key])
        except InvalidID:
            raise serializers.ValidationError('Invalid ID')

        if not issubclass(self.serializer_class.Meta.model, model):
            raise serializers.ValidationError('Invalid ID')

        self.kwargs[lookup_key] = str(id)

        return ret


class ShareObjectViewSet(viewsets.ReadOnlyModelViewSet):
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
