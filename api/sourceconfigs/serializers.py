from share import models

from api.base import ShareSerializer


class SourceConfigSerializer(ShareSerializer):
    class Meta:
        model = models.SourceConfig
        fields = (
            'label',
            'source',
            'disabled',
        )
