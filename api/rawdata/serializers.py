from share import models

from api.base import ShareSerializer


class RawDatumSerializer(ShareSerializer):

    class Meta:
        model = models.RawDatum
        fields = ('id', 'suid', 'datum', 'sha256', 'date_modified', 'date_created')
