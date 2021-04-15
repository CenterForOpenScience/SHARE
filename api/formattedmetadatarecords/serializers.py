from share import models

from api.base import ShareSerializer
from api.fields import ShareIdentityField


class FormattedMetadataRecordSerializer(ShareSerializer):
    # link to self
    url = ShareIdentityField(view_name='api:formattedmetadatarecord-detail')

    class Meta:
        model = models.FormattedMetadataRecord
        fields = (
            'suid',
            'record_format',
            'date_modified',
            'formatted_metadata',
            'url',
        )
