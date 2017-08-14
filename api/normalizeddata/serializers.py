from rest_framework_json_api import serializers

from share import models

# from api.base import ShareSerializer


class FullNormalizedDataSerializer(serializers.ModelSerializer):

    tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=False, queryset=models.CeleryTaskResult.objects.all())
    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source', 'raw', 'tasks')


class BasicNormalizedDataSerializer(serializers.ModelSerializer):

    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source')
