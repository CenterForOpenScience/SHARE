import re

from django.urls import reverse

from rest_framework import views, viewsets
from rest_framework.response import Response
from rest_framework_json_api import serializers

from share.util import IDObfuscator, InvalidID


__all__ = ('ShareViewSet', 'RootView')


class ShareViewSet(viewsets.ViewSet):
    ordering = ('-id', )

    def initial(self, request, *args, **kwargs):
        ret = super().initial(request, *args, **kwargs)

        lookup_key = self.lookup_url_kwarg or self.lookup_field
        if lookup_key not in self.kwargs:
            return ret
        lookup = self.kwargs[lookup_key]
        expected_model = self.get_serializer_class().Meta.model

        # Decode id's before the all the internal dispatching
        try:
            model, id = IDObfuscator().decode(lookup)
        except InvalidID:
            if re.fullmatch(r'\d+', lookup):
                # Allow primary keys for debugging convenience.
                # Mabye remove if people start abusing this to harvest by sequential PK.
                return ret
            raise serializers.ValidationError('Invalid ID')

        if not issubclass(expected_model, model):
            raise serializers.ValidationError('Invalid ID')

        self.kwargs[lookup_key] = str(id)

        return ret


class RootView(views.APIView):
    def get(self, request):
        links = {
            'site_banners': 'api:site_banners-list',
            'normalizeddata': 'api:normalizeddata-list',
            'rawdata': 'api:rawdatum-list',
            'sourceregistrations': 'api:sourceregistration-list',
            'sources': 'api:source-list',
            'users': 'api:user-list',
            'schema': 'api:schema',
            'status': 'api:status',
            'rss': 'api:rss',
            'atom': 'api:atom',
        }
        ret = {k: request.build_absolute_uri(reverse(v)) for k, v in links.items()}
        return Response(ret)
