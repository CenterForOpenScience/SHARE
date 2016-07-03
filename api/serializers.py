from rest_framework import serializers

from share import models


class RawDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RawData
        fields = ('source', 'provider_doc_id', 'data', 'sha256', 'date_seen', 'date_harvested')


class NormalizedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NormalizedData
        fields = ('created_at', 'normalized_data', 'source')


class ChangeSerializer(serializers.ModelSerializer):
    self = serializers.HyperlinkedIdentityField(view_name='api:change-detail')
    class Meta:
        model = models.Change
        fields = ('self', 'id', 'change', 'node_id', 'type', 'target', 'target_version')


class ChangeSetSerializer(serializers.ModelSerializer):
    changes = ChangeSerializer(many=True)
    self = serializers.HyperlinkedIdentityField(view_name='api:changeset-detail')

    class Meta:
        model = models.ChangeSet
        fields = ('self', 'submitted_at', 'submitted_by', 'changes')
