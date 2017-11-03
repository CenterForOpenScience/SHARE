from rest_framework_json_api import serializers

from share import models

from api.base import ShareSerializer


class ProviderRegistrationSerializer(ShareSerializer):
    status = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(read_only=True)
    submitted_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_status(self, obj):
        return models.ProviderRegistration.STATUS[obj.status]

    class Meta:
        model = models.ProviderRegistration
        fields = '__all__'
