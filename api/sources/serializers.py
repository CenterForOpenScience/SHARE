import logging

import requests

from share import models

from django.core.files.base import ContentFile
from django.db import transaction

from rest_framework_json_api import serializers

from api.base import ShareSerializer
from api.base import exceptions
from api.fields import ShareIdentityField
from api.users.serializers import ShareUserSerializer
from api.users.serializers import ShareUserWithTokenSerializer


logger = logging.getLogger(__name__)


class ReadonlySourceSerializer(ShareSerializer):
    # link to self
    url = ShareIdentityField(view_name='api:source-detail')

    class Meta:
        model = models.Source
        fields = (
            'name',
            'home_page',
            'long_title',
            'icon',
            'url',
            'source_configs',
        )
        read_only_fields = fields


class UpdateSourceSerializer(ShareSerializer):

    VALID_ICON_TYPES = ('image/png', 'image/jpeg')

    included_serializers = {
        'user': ShareUserWithTokenSerializer,
    }

    # link to self
    url = ShareIdentityField(view_name='api:source-detail')

    # URL to fetch the source's icon
    icon_url = serializers.URLField(write_only=True)

    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'canonical', 'icon', 'icon_url', 'user', 'url')
        read_only_fields = ('icon', 'user', 'url')
        view_name = 'api:source-detail'

    class JSONAPIMeta:
        included_resources = ['user']

    def update(self, instance, validated_data):
        # TODO: when long_title is changed, reindex works accordingly
        icon_url = validated_data.pop('icon_url', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if icon_url:
                icon_file = self._fetch_icon_file(icon_url)
                instance.icon.save(instance.name, content=icon_file)
            return instance

    def _fetch_icon_file(self, icon_url):
        try:
            r = requests.get(icon_url, timeout=5)
            header_type = r.headers['content-type'].split(';')[0].lower()
            if header_type not in self.VALID_ICON_TYPES:
                raise serializers.ValidationError('Invalid image type.')
            return ContentFile(r.content)
        except Exception as e:
            logger.warning('Exception occured while downloading icon %s', e)
            raise serializers.ValidationError('Could not download/process image.')


class CreateSourceSerializer(UpdateSourceSerializer):

    # Don't use validators to enforce uniqueness, so we can return the conflicting object
    class Meta(UpdateSourceSerializer.Meta):
        extra_kwargs = {
            'name': {'required': False, 'validators': []},
            'long_title': {'validators': []},
        }

    def create(self, validated_data):
        icon_url = validated_data.pop('icon_url')
        long_title = validated_data.pop('long_title')

        icon_file = self._fetch_icon_file(icon_url)

        username = long_title.replace(' ', '_').lower()
        name = validated_data.pop('name', username)

        with transaction.atomic():
            source, created = models.Source.objects.get_or_create(
                long_title=long_title,
                defaults={
                    'name': name,
                    'canonical': True,
                    **validated_data
                }
            )
            if not created:
                raise exceptions.AlreadyExistsError(source)

            user = self._create_trusted_user(username=username)
            source.user_id = user.id
            source.icon.save(name, content=icon_file)

            return source

    def _create_trusted_user(self, username):
        user_serializer = ShareUserSerializer(
            data={'username': username, 'is_trusted': True},
            context={'request': self.context['request']}
        )

        user_serializer.is_valid(raise_exception=True)

        user = user_serializer.save()
        user.set_unusable_password()
        user.save()
        return user
