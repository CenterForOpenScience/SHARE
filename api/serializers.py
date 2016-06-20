from rest_framework import serializers

from share import models


class RawDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RawData
        fields = ('source', 'provider_doc_id', 'data', 'sha256', 'date_seen', 'date_harvested')


class NormalizedManuscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NormalizedManuscript
        fields = ('raw_data', 'processed_at', 'normalized_data')
