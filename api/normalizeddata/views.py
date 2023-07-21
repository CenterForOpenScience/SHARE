import logging
import json

from django.urls import reverse
from rest_framework import status
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
import sentry_sdk

from share import models as share_db
from share.util.graph import MutableGraph
from share.util.osf import guess_osf_guid
from api.base.views import ShareViewSet
from api.normalizeddata.serializers import BasicNormalizedDataSerializer
from api.normalizeddata.serializers import FullNormalizedDataSerializer
from api.pagination import CursorPagination
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from trove import digestive_tract


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
        return share_db.NormalizedData.objects.all()

    def create(self, request, *args, **kwargs):
        if share_db.FeatureFlag.objects.flag_is_up(share_db.FeatureFlag.IGNORE_SHAREV2_INGEST):
            return Response({
                'errors': [
                    {'detail': (
                        'this route was deprecated and has been removed'
                        f' (use {reverse("trove:ingest-rdf")} instead)'
                    )},
                ],
            }, status=status.HTTP_410_GONE)
        try:
            return self._do_create(request, *args, **kwargs)
        except Exception:
            sentry_sdk.capture_exception()  # get some insight into common validation errors
            raise

    def _do_create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data['data']
        suid = serializer.validated_data.get('suid', None)
        if not suid:
            # HACK: try for an osf guid -- may still be None tho
            suid = guess_osf_guid(MutableGraph.from_jsonld(data))
            if not suid:
                raise ValidationError("'suid' is a required attribute")
        _task_id = digestive_tract.swallow__sharev2_legacy(
            from_user=request.user,
            record=json.dumps(data, sort_keys=True),
            record_identifier=suid,
            transformer_key='v2_push',
            urgent=True,
        )
        return Response({
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'task': _task_id,
                },
            },
            'meta': {
                'warning': (
                    'this route is deprecated and may be removed'
                    f' (consider {reverse("trove:ingest-rdf")} instead)'
                ),
            },
        }, status=status.HTTP_202_ACCEPTED)
