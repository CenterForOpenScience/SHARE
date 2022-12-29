import logging
from django.db import transaction
from django.urls import reverse

from raven.contrib.django.raven_compat.models import client as sentry_client

from rest_framework import status
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from share import models
from share.util import IDObfuscator
from share.util.graph import MutableGraph
from share.util.osf import guess_osf_guid
from share.push import ingest

from api.base.views import ShareViewSet
from api.normalizeddata.serializers import BasicNormalizedDataSerializer
from api.normalizeddata.serializers import FullNormalizedDataSerializer
from api.pagination import CursorPagination
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated


logger = logging.getLogger(__name__)


class NormalizedDataViewSet(ShareViewSet, generics.ListCreateAPIView, generics.RetrieveAPIView):
    """View showing all normalized data in the SHARE Dataset.

    ## Submitting changes to the SHARE dataset
    Changes, whether they are additions or modifications, are submitted as a subset of [JSON-LD graphs](https://www.w3.org/TR/json-ld/#named-graphs).
    Each [node](https://www.w3.org/TR/json-ld/#dfn-node) of the graph MUST contain both an `@id` and `@type` key.

        Method:        POST
        Body (JSON):   {
                        'data': {
                            'type': 'NormalizedData'
                            'attributes': {
                                'data': {
                                    '@graph': [{
                                        '@type': <type of document, exp: person>,
                                        '@id': <_:random>,
                                        <attribute_name>: <value>,
                                        <relationship_name>: {
                                            '@type': <type>,
                                            '@id': <id>
                                        }
                                    }]
                                }
                            }
                        }
                       }
        Success:       200 OK
    """
    ordering = ('-id', )
    pagination_class = CursorPagination
    permission_classes = (ReadOnlyOrTokenHasScopeOrIsAuthenticated, )
    required_scopes = ('upload_normalized_manuscript', )
    resource_name = 'NormalizedData'

    def get_serializer_class(self):
        if not self.request.user.is_authenticated:
            return BasicNormalizedDataSerializer
        elif self.request.user.is_robot:
            return FullNormalizedDataSerializer
        return BasicNormalizedDataSerializer

    def get_queryset(self):
        return models.NormalizedData.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            return self._do_create(request, *args, **kwargs)
        except Exception as e:
            sentry_client.captureMessage('Bad normalizeddatum?', data={
                'request': {
                    'path': request.path,
                    'method': request.method,
                    'user': request.user,
                },
            }, extra={
                'error': str(e),
            })
            raise

    def _do_create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        datum = serializer.validated_data['data']
        datum_identifier = serializer.validated_data.get('suid', None)
        if not datum_identifier:
            # HACK: try for an osf guid -- may still be None tho
            datum_identifier = guess_osf_guid(MutableGraph.from_jsonld(datum))
            if not datum_identifier:
                raise ValidationError("'suid' is a required attribute")
        suid = ingest.chew(
            datum=datum,
            datum_identifier=datum_identifier,
            datum_contenttype=request.content_type,
            user=request.user,
        )
        ingest_job = ingest.swallow(suid, urgent=True)
        ingest_job_uri = request.build_absolute_uri(
            reverse('api:ingestjob-detail', args=[IDObfuscator.encode(ingest_job)]),
        )
        return Response({'ingest_job': ingest_job_uri}, status=status.HTTP_202_ACCEPTED)
