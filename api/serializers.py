from django.contrib.auth.models import AnonymousUser

from rest_framework_json_api import serializers

from share import models
from share.models import ProviderRegistration, SiteBanner, CeleryTaskResult

from api.base import ShareSerializer


class RawDatumSerializer(ShareSerializer):

    class Meta:
        model = models.RawDatum
        fields = ('id', 'suid', 'datum', 'sha256', 'date_modified', 'date_created', 'logs')


class ProviderRegistrationSerializer(ShareSerializer):
    status = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(read_only=True)
    submitted_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_status(self, obj):
        return ProviderRegistration.STATUS[obj.status]

    class Meta:
        model = models.ProviderRegistration
        fields = '__all__'


class FullNormalizedDataSerializer(serializers.ModelSerializer):

    tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=False, queryset=CeleryTaskResult.objects.all())
    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source', 'raw', 'tasks')


class BasicNormalizedDataSerializer(serializers.ModelSerializer):

    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source')


class ShareUserSerializer(ShareSerializer):
    def __init__(self, *args, token=None, **kwargs):
        super().__init__(*args, **kwargs)
        if token:
            self.fields.update({
                'token': serializers.SerializerMethodField()
            })
        self.fields.update({
            '🦄': serializers.SerializerMethodField(method_name='is_superuser'),
            '🤖': serializers.SerializerMethodField(method_name='is_robot'),
        })

    def is_robot(self, obj):
        if not isinstance(obj, AnonymousUser):
            return obj.is_robot
        return False

    def get_token(self, obj):
        try:
            return obj.accesstoken_set.first().token
        except AttributeError:
            return None

    def is_superuser(self, obj):
        return obj.is_superuser

    class Meta:
        model = models.ShareUser
        fields = (
            'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login',
            'is_active', 'gravatar', 'locale', 'time_zone', 'is_trusted'
        )


class SourceSerializer(ShareSerializer):
    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'icon')


class SiteBannerSerializer(ShareSerializer):
    color = serializers.SerializerMethodField()

    def get_color(self, obj):
        return SiteBanner.COLOR[obj.color]

    class Meta:
        model = models.SiteBanner
        fields = ('title', 'description', 'color', 'icon')
