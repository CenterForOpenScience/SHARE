import logging

import requests

from share import models

from django.core.files.base import ContentFile
from django.db import transaction

from rest_framework.serializers import ValidationError

from api.base import ShareSerializer
from api.users.serializers import ShareUserSerializer
from api.users.serializers import ShareUserWithTokenSerializer
from api.source_configs.serializers import SourceConfigSerializer


logger = logging.getLogger(__name__)


class SourceSerializer(ShareSerializer):
    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'icon')


class WritableSourceSerializer(ShareSerializer):

    VALID_ICON_TYPES = ('image/png', 'image/jpeg')

    included_serializers = {
        'source_configs': SourceConfigSerializer,
        'user': ShareUserWithTokenSerializer,
    }

    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'icon', 'user', 'source_configs')
        read_only_fields = ('user', 'source_configs')

    class JSONAPIMeta:
        included_resources = ['user', 'source_configs']

    def get_source_config(self, obj):
        return obj.source_configs.first()

    def create(self, validated_data):
        icon_url = validated_data.pop('icon')
        icon_file = self._fetch_icon_file(icon_url)
        long_title = validated_data['long_title']

        label = long_title.replace(' ', '_').lower()

        name = validated_data.get('name', label)

        with transaction.atomic():
            user = self._create_trusted_user(username=label)
            source = models.Source(
                user_id=user.id,
                long_title=long_title,
                home_page=validated_data.get('home_page', None),
                name=name,
            )
            source.save()
            source.icon.save(name, content=icon_file)

            models.SourceConfig.objects.create(source_id=source.id, label=label)

            return source

    def _fetch_icon_file(self, icon_url):
        try:
            r = requests.get(icon_url, timeout=5)
            header_type = r.headers['content-type'].split(';')[0].lower()
            if header_type not in self.VALID_ICON_TYPES:
                raise ValidationError('Invalid image type.')
            return ContentFile(r.content)
        except Exception as e:
            logger.warning('Exception occured while downloading icon %s', e)
            raise ValidationError('Could not download/process image.')

    def _create_trusted_user(self, username):
        user_serializer = ShareUserSerializer(
            data={'username': username, 'is_trusted': True},
            context={'request': self.context['request']}
        )

        user_serializer.is_valid(raise_exception=True)

        return user_serializer.save()
