import jsonschema

from django.db import transaction

from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from api import schemas
from api.authentication import APIV1TokenBackPortAuthentication
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.serializers import FullNormalizedDataSerializer, BasicNormalizedDataSerializer, \
    RawDatumSerializer, ShareUserSerializer, ProviderSerializer
from share.models import RawDatum, ShareUser, NormalizedData
from share.tasks import DisambiguatorTask
from share.harvest.base import BaseHarvester
from share.transform.v1_push import V1Transformer


__all__ = ('NormalizedDataViewSet', 'RawDatumViewSet', 'ShareUserViewSet', 'ProviderViewSet', 'V1DataView')


class ShareUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns details about the currently logged in user
    """
    serializer_class = ShareUserSerializer

    def get_queryset(self):
        return [self.request.user, ]


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderSerializer

    def get_queryset(self):
        queryset = ShareUser.objects.exclude(robot='').exclude(long_title='')
        sort = self.request.query_params.get("sort")
        if sort:
            return queryset.order_by(sort)
        return queryset


class NormalizedDataViewSet(viewsets.ModelViewSet):
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
    permission_classes = [ReadOnlyOrTokenHasScopeOrIsAuthenticated, ]
    required_scopes = ['upload_normalized_manuscript', ]
    resource_name = 'NormalizedData'

    def get_serializer_class(self):
        if not self.request.user.is_authenticated():
            return BasicNormalizedDataSerializer
        elif self.request.user.is_robot:
            return FullNormalizedDataSerializer
        return BasicNormalizedDataSerializer

    def get_queryset(self):
        return NormalizedData.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            nm_instance = serializer.save()
            async_result = DisambiguatorTask().delay(request.user.id, nm_instance.id)
            # TODO Fix Me
            return Response({
                'id': nm_instance.id,
                'type': 'NormalizedData',
                'attributes': {'task': async_result.id}
            }, status=status.HTTP_202_ACCEPTED)


class RawDatumViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Raw data, exactly as harvested from the data source.

    ## Query by object
    To get all the raw data corresponding to a Share object, use the query
    parameters `object_id=<@id>` and `object_type=<@type>`
    """

    serializer_class = RawDatumSerializer

    def get_queryset(self):
        object_id = self.request.query_params.get('object_id', None)
        object_type = self.request.query_params.get('object_type', None)
        if object_id and object_type:
            return RawDatum.objects.filter(
                normalizeddata__changeset__changes__target_id=object_id,
                normalizeddata__changeset__changes__target_type__model=object_type
            ).distinct('id')
        else:
            return RawDatum.objects.all()


class V1DataView(views.APIView):
    """View allowing sources to post SHARE v1 formatted metadata directly to the SHARE Dataset.

    ## Submit Data in SHARE v1 Format
    Please note that this endpoint is to ease the transition from SHARE v1 to SHARE v2 and sources
    are encouraged to transition to submitting metadata in the SHARE v2 format.

    Submitting data through the normalizeddata endpoint is strongly preferred as support for
    the v1 format will not be continued.

    v1 Format

        For the full format please see https://github.com/erinspace/shareregistration/blob/master/push_endpoint/schemas.py

        Required Fields: [
            "title",
            "contributors",
            "uris",
            "providerUpdatedDateTime"
        ],

    Create

        Method:        POST
        Body (JSON): {
                        {
                            "jsonData": {
                                "publisher":{
                                    "name": <publisher name>,
                                    "uri": <publisher uri>
                                },
                                "description": <description>,
                                "contributors":[
                                    {
                                        "name":<contributor name>,
                                        "email": <email>,
                                        "sameAs": <uri>
                                    },
                                    {
                                        "name":<contributor name>
                                    }
                                ],
                                "title": <title>,
                                "tags":[
                                    <tag>,
                                    <tag>
                                ],
                                "languages":[
                                    <language>
                                ],
                                "providerUpdatedDateTime": <time submitted>,
                                "uris": {
                                    "canonicalUri": <uri>,
                                    "providerUris":[
                                        <uri>
                                    ]
                                }
                            }
                        }
                    }
        Success:       200 OK
    """
    authentication_classes = (APIV1TokenBackPortAuthentication, )
    permission_classes = [ReadOnlyOrTokenHasScopeOrIsAuthenticated, ]
    serializer_class = BasicNormalizedDataSerializer
    renderer_classes = (JSONRenderer, )
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):

        try:
            jsonschema.validate(request.data, schemas.v1_push_schema)
        except (jsonschema.exceptions.ValidationError) as error:
            raise ParseError(detail=error.message)

        try:
            prelim_data = request.data['jsonData']
        except ParseError as error:
            return Response(
                'Invalid JSON - {0}'.format(error.message),
                status=status.HTTP_400_BAD_REQUEST
            )

        app_label = request.user.username

        # store raw data, assuming you can only submit one at a time
        raw = None
        with transaction.atomic():
            try:
                doc_id = prelim_data['uris']['canonicalUri']
            except KeyError:
                return Response({'errors': 'Canonical URI not found in uris.', 'data': prelim_data}, status=status.HTTP_400_BAD_REQUEST)

            raw = RawDatum.objects.store_data(doc_id, BaseHarvester.encode_json(self, prelim_data), request.user, app_label)

        # normalize data
        normalized_data = V1Transformer({}).transform(raw.data)
        data = {}
        data['data'] = normalized_data
        serializer = BasicNormalizedDataSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            nm_instance = serializer.save()
            async_result = DisambiguatorTask().delay(request.user.id, nm_instance.id)
            return Response({'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'errors': serializer.errors, 'data': prelim_data}, status=status.HTTP_400_BAD_REQUEST)
