from collections import OrderedDict

from django.contrib.auth.models import AnonymousUser

from rest_framework_json_api import serializers

from share import models
from share.models import ChangeSet, ProviderRegistration, CeleryProviderTask, SiteBanner

from api import fields


class BaseShareSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        # super hates my additional kwargs
        sparse = kwargs.pop('sparse', False)
        version_serializer = kwargs.pop('version_serializer', False)
        super(BaseShareSerializer, self).__init__(*args, **kwargs)

        if sparse:
            # clear the fields if they asked for sparse
            self.fields.clear()
        else:
            # remove hidden fields
            excluded_fields = ['change', 'sources']
            for field_name in tuple(self.fields.keys()):
                if 'version' in field_name or field_name in excluded_fields:
                    self.fields.pop(field_name)

            if not version_serializer:
                # add links to related objects
                self.fields.update({
                    'links': fields.LinksField(links=self.Meta.links, source='*')
                })

        # version specific fields
        if version_serializer:
            self.fields.update({
                'action': serializers.CharField(max_length=10),
                'persistent_id': serializers.IntegerField()
            })

        # add fields with improper names
        self.fields.update({
            'type': fields.TypeField(),
        })

    class Meta:
        links = ('versions', 'changes', 'rawdata')

    # http://stackoverflow.com/questions/27015931/remove-null-fields-from-django-rest-framework-response
    def to_representation(self, instance):
        ret = super(BaseShareSerializer, self).to_representation(instance)
        ret = OrderedDict(list(filter(lambda x: x[1] is not None, ret.items())))
        return ret


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


class FullNormalizedDataSerializer(serializers.ModelSerializer):

    tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=False, queryset=CeleryProviderTask.objects.all())
    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source', 'raw', 'tasks')


class BasicNormalizedDataSerializer(serializers.ModelSerializer):

    source = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.NormalizedData
        fields = ('data', 'source')


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

    def get_favicon(self, obj):
        return obj.favicon.url if obj.favicon else None

    class Meta:
        model = models.ShareUser
        fields = (
            'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login',
            'is_active', 'gravatar', 'locale', 'time_zone', 'favicon'
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
        fields = ('home_page', 'long_title', 'date_joined', 'gravatar', 'favicon')


class SiteBannerSerializer(ShareModelSerializer):
    color = serializers.SerializerMethodField()

    def get_color(self, obj):
        return SiteBanner.COLOR[obj.color]

    class Meta:
        model = models.SiteBanner
        fields = ('title', 'description', 'color', 'icon')
