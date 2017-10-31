from share import models

from api.base import ShareSerializer


# TODO make an endpoint for SourceConfigs
class SourceConfigSerializer(ShareSerializer):
    class Meta:
        model = models.SourceConfig
        fields = ('label',)
