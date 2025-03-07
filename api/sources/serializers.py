import logging
import re

from share import models

from django.db import transaction

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

    class Meta:
        model = models.Source
        fields = ('name', 'home_page', 'long_title', 'canonical', 'user', 'url')
        read_only_fields = ('user', 'url')
        view_name = 'api:source-detail'

    class JSONAPIMeta:
        included_resources = ['user']


class CreateSourceSerializer(UpdateSourceSerializer):

    # Don't use validators to enforce uniqueness, so we can return the conflicting object
    class Meta(UpdateSourceSerializer.Meta):
        extra_kwargs = {
            'name': {'required': False, 'validators': []},
            'long_title': {'validators': []},
        }

    def create(self, validated_data):
        long_title = validated_data.pop('long_title')

        username = re.sub(r'[^\w.@+-]', '_', long_title).lower()
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
            source.save()
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
