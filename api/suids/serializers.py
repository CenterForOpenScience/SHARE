from share import models

from api.base import ShareSerializer
from api.fields import ShareIdentityField
from api.sourceconfigs.serializers import SourceConfigSerializer


class SuidSerializer(ShareSerializer):
    included_serializers = {
        'source_config': SourceConfigSerializer,
    }

    # link to self
    url = ShareIdentityField(view_name='api:suid-detail')

    class Meta:
        model = models.SourceUniqueIdentifier
        fields = (
            'identifier',
            'source_config',
            'url',
        )
