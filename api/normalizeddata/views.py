from django.db import transaction

from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response

from share import models
from share.tasks import ingest
from share.util import IDObfuscator

from api.base.views import ShareViewSet
from api.normalizeddata.serializers import BasicNormalizedDataSerializer
from api.normalizeddata.serializers import FullNormalizedDataSerializer
from api.pagination import CursorPagination
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.util import absolute_reverse


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
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            source_config = models.SourceConfig.objects.get_or_create_push_config(request.user, 'v2_push')
            nm_instance = serializer.save()
            nm_instance.raw = models.RawDatum.objects.store_json(source_config, nm_instance.data)
            nm_instance.save()

            job = models.IngestJob.schedule(nm_instance.raw)
            async_result = ingest.delay(job_id=job.id, exhaust=False)

            # TODO Use an actual serializer
            return Response({
                'id': IDObfuscator.encode(nm_instance),
                'type': 'NormalizedData',
                'attributes': {
                    'task': async_result.id,
                    'ingest_job': absolute_reverse('api:ingestjob-detail', args=[IDObfuscator.encode(job)]),
                }
            }, status=status.HTTP_202_ACCEPTED)
