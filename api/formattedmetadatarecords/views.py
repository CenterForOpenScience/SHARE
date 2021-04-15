from rest_framework import viewsets

from api.formattedmetadatarecords.serializers import FormattedMetadataRecordSerializer
from api.base import ShareViewSet

from share.models import FormattedMetadataRecord


class FormattedMetadataRecordViewSet(ShareViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = FormattedMetadataRecordSerializer

    ordering = ('id', )

    def get_queryset(self):
        return FormattedMetadataRecord.objects.all()
