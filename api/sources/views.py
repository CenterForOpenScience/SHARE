import logging

import requests

from django.core.files.base import ContentFile
from django.db import transaction

from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from share import models
from share.util import IDObfuscator

from api.sources.serializers import SourceSerializer
from api.users.serializers import ShareUserSerializer


logger = logging.getLogger(__name__)


class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.OrderingFilter, )
    ordering = ('id', )
    ordering_fields = ('long_title', )
    permission_classes = (DjangoModelPermissionsOrAnonReadOnly, )
    serializer_class = SourceSerializer

    queryset = models.Source.objects.none()  # Required for DjangoModelPermissions

    VALID_IMAGE_TYPES = ('image/png', 'image/jpeg')

    def get_queryset(self):
        return models.Source.objects.exclude(icon='').exclude(is_deleted=True)

    def create(self, request, *args, **kwargs):
        try:
            long_title = request.data['long_title']
            icon = request.data['icon']
        except KeyError as e:
            raise ValidationError('{} is a required attribute.'.format(e))

        try:
            r = requests.get(icon, timeout=5)
            header_type = r.headers['content-type'].split(';')[0].lower()
            if header_type not in self.VALID_IMAGE_TYPES:
                raise ValidationError('Invalid image type.')

            icon_file = ContentFile(r.content)
        except Exception as e:
            logger.warning('Exception occured while downloading icon %s', e)
            raise ValidationError('Could not download/process image.')

        label = long_title.replace(' ', '_').lower()

        user_serializer = ShareUserSerializer(
            data={'username': label, 'is_trusted': True},
            context={'request': request}
        )

        user_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user_instance = user_serializer.save()
            source_instance = models.Source(
                user_id=user_instance.id,
                long_title=long_title,
                home_page=request.data.get('home_page', None),
                name=label,
            )
            source_instance.icon.save(label, content=icon_file)
            source_config_instance = models.SourceConfig.objects.create(source_id=source_instance.id, label=label)

        return Response(
            {
                'id': IDObfuscator.encode(source_instance),
                'type': 'Source',
                'attributes': {
                    'long_title': source_instance.long_title,
                    'name': source_instance.name,
                    'home_page': source_instance.home_page
                },
                'relationships': {
                    'share_user': {
                        'data': {
                            'id': IDObfuscator.encode(user_instance),
                            'type': 'ShareUser',
                            'attributes': {
                                'username': user_instance.username,
                                'authorization_token': user_instance.accesstoken_set.first().token
                            }
                        }
                    },
                    'source_config': {
                        'data': {
                            'id': IDObfuscator.encode(source_config_instance),
                            'type': 'SourceConfig',
                            'attributes': {
                                'label': source_config_instance.label
                            }
                        }
                    }
                }
            },
            status=status.HTTP_201_CREATED
        )
