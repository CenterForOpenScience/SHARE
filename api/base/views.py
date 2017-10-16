from rest_framework import views, viewsets
from rest_framework.response import Response
from rest_framework_json_api import serializers

from share.util import IDObfuscator, InvalidID
from api.util import absolute_reverse


__all__ = ('ShareViewSet', 'RootView')


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

        if not issubclass(self.get_serializer_class().Meta.model, model):
            raise serializers.ValidationError('Invalid ID')

        self.kwargs[lookup_key] = str(id)

        return ret


class RootView(views.APIView):
    def get(self, request):
        ret = {
            'site_banners': absolute_reverse('api:site_banners-list'),
            'normalizeddata': absolute_reverse('api:normalizeddata-list'),
            'rawdata': absolute_reverse('api:rawdatum-list'),
            'sourceregistrations': absolute_reverse('api:sourceregistration-list'),
            'sources': absolute_reverse('api:source-list'),
            'users': absolute_reverse('api:user-list'),
            'schema': absolute_reverse('api:schema'),
            'status': absolute_reverse('api:status'),
            'rss': absolute_reverse('api:rss'),
            'atom': absolute_reverse('api:atom'),
        }
        return Response(ret)
