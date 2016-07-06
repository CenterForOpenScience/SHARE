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
        fields = ('self', 'submitted_at', 'changes')


class ShareUserSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ShareUserSerializer, self).__init__(*args, **kwargs)
        self.fields.update({
            '🦄': serializers.SerializerMethodField(method_name='is_superuser'),
            '🤖': serializers.SerializerMethodField(method_name='is_robot'),
        })
    token = serializers.SerializerMethodField()

    def is_robot(self, obj):
        return obj.is_robot

    def get_token(self, obj):
        try:
            return obj.socialaccount_set.first().socialtoken_set.first().token
        except AttributeError:
            return None

    def is_superuser(self, obj):
        return obj.is_superuser

    class Meta:
        model = models.ShareUser
        fields = ('username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login', 'is_active', 'token', 'gravatar', 'locale', 'time_zone')
