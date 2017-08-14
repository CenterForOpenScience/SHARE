from rest_framework import viewsets
from rest_framework_json_api import serializers

from share.util import IDObfuscator, InvalidID


__all__ = ('ShareViewSet', )


class ShareViewSet(viewsets.ViewSet):
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
