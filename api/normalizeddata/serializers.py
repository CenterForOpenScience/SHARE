from rest_framework_json_api import serializers

from share import models

from api import fields


class FullNormalizedDataSerializer(serializers.ModelSerializer):
    # link to self
    url = fields.ShareIdentityField(view_name='api:normalizeddata-detail')

    tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=False, queryset=models.CeleryTaskResult.objects.all())
    source = serializers.HiddenField(default=serializers.CurrentUserDefault())
    suid = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source', 'raw', 'tasks', 'url', 'suid')


class BasicNormalizedDataSerializer(serializers.ModelSerializer):
    # link to self
    url = fields.ShareIdentityField(view_name='api:normalizeddata-detail')

    source = serializers.HiddenField(default=serializers.CurrentUserDefault())
    suid = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source', 'url', 'suid')
