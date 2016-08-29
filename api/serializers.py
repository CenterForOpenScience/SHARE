from django.contrib.auth.models import AnonymousUser
from rest_framework import serializers

from share import models
from share.models import ChangeSet


class RawDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RawData
        fields = ('source', 'app_label', 'provider_doc_id', 'data', 'sha256', 'date_seen', 'date_harvested')


class NormalizedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NormalizedData
        fields = ('created_at', 'normalized_data', 'source')


class ChangeSerializer(serializers.ModelSerializer):
    self = serializers.HyperlinkedIdentityField(view_name='api:change-detail')

    class Meta:
        model = models.Change
        fields = ('self', 'id', 'change', 'node_id', 'type', 'target_version', 'target_type', 'target_id')


class ShareUserSerializer(serializers.ModelSerializer):
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


class ChangeSetSerializer(serializers.ModelSerializer):
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
        fields = ('self', 'submitted_at', 'change_count', 'source', 'status')


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
