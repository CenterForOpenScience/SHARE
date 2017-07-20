from rest_framework import viewsets

from share.util import IDObfuscator, InvalidID

from api.pagination import CursorPagination
from api.permissions import IsDeletedPremissions


__all__ = ('ShareObjectViewSet', )


class ShareObjectViewSet(viewsets.ReadOnlyModelViewSet):
    ordering = ('-id', )
    pagination_class = CursorPagination
    permission_classes = (IsDeletedPremissions, )

    # Can't expose these until we have indexes added, both ascending and descending
    # filter_backends = (filters.OrderingFilter,)
    # ordering_fields = ('id', 'date_updated')

    def dispatch(self, request, *args, **kwargs):
        if self.lookup_field in kwargs:
            kwargs[self.lookup_field] = IDObfuscator.decode_id(kwargs[self.lookup_field])
        return super().dispatch(request, *args, **kwargs)

    # Override get_queryset to handle items marked as deleted.
    def get_queryset(self, list=True):
        queryset = super().get_queryset()
        if list and hasattr(queryset.model, 'is_deleted'):
            return queryset.exclude(is_deleted=True)
        return queryset

    # Override to convert encoded pk to an actual pk
    # def get_object(self):
    #     import ipdb; ipdb.set_trace()
    #     return super().get_object()
        # queryset = self.filter_queryset(self.get_queryset(False))

    #     # Perform the lookup filtering.
    #     lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

    #     assert lookup_url_kwarg in self.kwargs, (
    #         'Expected view %s to be called with a URL keyword argument '
    #         'named "%s". Fix your URL conf, or set the `.lookup_field` '
    #         'attribute on the view correctly.' %
    #         (self.__class__.__name__, lookup_url_kwarg)
    #     )

    #     try:
    #         (model, decoded_pk) = IDObfuscator.decode(self.kwargs[lookup_url_kwarg])
    #         concrete_model = self.serializer_class.Meta.model._meta.concrete_model
    #         if model is not concrete_model:
    #             raise serializers.ValidationError('The specified ID refers to an {}. Expected {}'.format(model._meta.model_name, concrete_model._meta.model_name))
    #     except InvalidID:
    #         raise serializers.ValidationError('Invalid ID')

    #     filter_kwargs = {self.lookup_field: decoded_pk}
    #     obj = get_object_or_404(queryset, **filter_kwargs)

    #     # May raise a permission denied
    #     self.check_object_permissions(self.request, obj)

    #     return obj
