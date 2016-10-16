from collections import OrderedDict

from django.contrib.auth.models import AnonymousUser

from rest_framework_json_api import serializers

from share import models
from share.models import ChangeSet, ProviderRegistration


class ShareModelSerializer(serializers.ModelSerializer):
    # http://stackoverflow.com/questions/27015931/remove-null-fields-from-django-rest-framework-response
    def to_representation(self, instance):
        def not_none(value):
            return value is not None

        ret = super(ShareModelSerializer, self).to_representation(instance)
        ret = OrderedDict(list(filter(lambda x: not_none(x[1]), ret.items())))
        return ret


class RawDataSerializer(ShareModelSerializer):
    class Meta:
        model = models.RawData
        fields = ('id', 'source', 'app_label', 'provider_doc_id', 'data', 'sha256', 'date_seen', 'date_harvested')


class ProviderRegistrationSerializer(ShareModelSerializer):
    status = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(read_only=True)
    submitted_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_status(self, obj):
        return ProviderRegistration.STATUS[obj.status]

    class Meta:
        model = models.ProviderRegistration
        fields = '__all__'


class NormalizedDataSerializer(ShareModelSerializer):

    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('created_at', 'data', 'source')


class ChangeSerializer(ShareModelSerializer):
    self = serializers.HyperlinkedIdentityField(view_name='api:change-detail')
    target_type = serializers.StringRelatedField()

    class Meta:
        model = models.Change
        fields = ('self', 'id', 'change', 'node_id', 'type', 'target_type', 'target_id')


class ShareUserSerializer(ShareModelSerializer):
    def __init__(self, *args, token=None, **kwargs):
        super(ShareUserSerializer, self).__init__(*args, **kwargs)
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
            'is_active', 'gravatar', 'locale', 'time_zone'
        )


class ChangeSetSerializer(ShareModelSerializer):
    # changes = ChangeSerializer(many=True)
    change_count = serializers.SerializerMethodField()
    self = serializers.HyperlinkedIdentityField(view_name='api:changeset-detail')
    source = ShareUserSerializer(source='normalized_data.source')
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return ChangeSet.STATUS[obj.status]

    def get_change_count(self, obj):
        return obj.changes.count()

    class Meta:
        model = models.ChangeSet
        fields = ('self', 'id', 'submitted_at', 'change_count', 'source', 'status')


class ProviderSerializer(ShareUserSerializer):
    def __init__(self, *args, **kwargs):
        super(ShareUserSerializer, self).__init__(*args, **kwargs)
        self.fields.update({
            '🤖': serializers.SerializerMethodField(method_name='is_robot'),
            'provider_name': serializers.SerializerMethodField(method_name='provider_name')
        })

    def provider_name(self, obj):
        return obj.username.replace('providers.', '')

    class Meta:
        model = models.ShareUser
        fields = ('home_page', 'long_title', 'date_joined', 'gravatar')
