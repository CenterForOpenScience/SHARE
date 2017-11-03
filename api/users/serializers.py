from django.contrib.auth.models import AnonymousUser

from rest_framework_json_api import serializers

from share import models

from api.base import ShareSerializer


class ShareUserSerializer(ShareSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update({
            '🦄': serializers.SerializerMethodField(method_name='is_superuser'),
            '🤖': serializers.SerializerMethodField(method_name='is_robot'),
        })

    def is_robot(self, obj):
        if not isinstance(obj, AnonymousUser):
            return obj.is_robot
        return False

    def is_superuser(self, obj):
        return obj.is_superuser

    class Meta:
        model = models.ShareUser
        fields = (
            'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login',
            'is_active', 'gravatar', 'locale', 'time_zone', 'is_trusted'
        )


class ShareUserWithTokenSerializer(ShareUserSerializer):
    token = serializers.SerializerMethodField()

    def get_token(self, obj):
        try:
            return obj.accesstoken_set.first().token
        except AttributeError:
            return None

    class Meta(ShareUserSerializer.Meta):
        fields = ShareUserSerializer.Meta.fields + ('token',)
