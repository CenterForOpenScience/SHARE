from share import models

from api.base import ShareSerializer


class SourceSerializer(ShareSerializer):
    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'icon')
