import jsonschema

from django.apps import apps
from django.db import transaction

from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from api import schemas
from api.authentication import APIV1TokenBackPortAuthentication
from api.filters import ChangeSetFilterSet, ChangeFilterSet
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.serializers import NormalizedDataSerializer, ChangeSetSerializer, ChangeSerializer, RawDataSerializer, \
    ShareUserSerializer, ProviderSerializer
from share.models import ChangeSet, Change, RawData, ShareUser, NormalizedData
from share.models.validators import JSONLDValidator
from share.tasks import MakeJsonPatches
from share.harvest.harvester import Harvester
from share.normalize.v1_push import V1Normalizer


__all__ = ('NormalizedDataViewSet', 'ChangeSetViewSet', 'ChangeViewSet', 'RawDataViewSet', 'ShareUserViewSet', 'ProviderViewSet', 'SchemaView', 'ModelSchemaView', 'V1DataView')


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

    ## Submit Changesets
    Change sets are submitted under @graph, described [here](https://www.w3.org/TR/json-ld/#named-graphs).
    Known ids and not known @ids use the format described [here](https://www.w3.org/TR/json-ld/#node-identifiers). Not known ids looks like '_:<randomstring>'

    Create

        Method:        POST
        Body (JSON):   {
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
        Success:       200 OK

    Update

        Method:        POST
        Body (JSON):   {
                        'data': {
                            '@graph': [{
                                '@type': <type of document, exp: person>,
                                '@id': <id>,
                                <attribute_name>: <value>,
                                <relationship_name>: {
                                    '@type': <type>,
                                    '@id': <id>
                                }
                            }]
                        }
                       }
        Success:       200 OK

    Merge

        Method:        POST
        Body (JSON):   {
                        'data': {
                            '@graph': [{
                                '@type': 'mergeAction',
                                '@id': <_:random>,
                                'into': {
                                    '@type': <type of document>,
                                    '@id': <doc id>
                                },
                                'from': {
                                    '@type': <same type of document>,
                                    '@id': <doc id>
                                }
                            }]
                        }
                       }
        Success:       200 OK
    """
    permission_classes = [ReadOnlyOrTokenHasScopeOrIsAuthenticated, ]
    serializer_class = NormalizedDataSerializer
    required_scopes = ['upload_normalized_manuscript', ]

    def get_queryset(self):
        return NormalizedData.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = NormalizedDataSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            nm_instance = serializer.save()
            async_result = MakeJsonPatches().delay(nm_instance.id, request.user.id)
            return Response({'normalized_id': nm_instance.id, 'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)


class ChangeSetViewSet(viewsets.ModelViewSet):
    """
    ChangeSets are items that have been added to the SHARE dataset but may not yet have been accepted.

    These can come from harvesters and normalizers or from the curate interface.

    ## Get Info

        Method:        GET
        Query Params:  `submitted_by=<Int>` -- share user that submitted the changeset
        Success:       200 OK

    ## Submit changes
        Look at `/api/normalizeddata/`
    """
    serializer_class = ChangeSetSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]

    def get_queryset(self):
        return ChangeSet.objects.all().select_related('normalized_data__source')
    filter_class = ChangeSetFilterSet


class ChangeViewSet(viewsets.ModelViewSet):
    serializer_class = ChangeSerializer
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    queryset = Change.objects.all()
    filter_class = ChangeFilterSet


class RawDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Raw data, exactly as harvested from the data source.

    ## Query by object
    To get all the raw data corresponding to a Share object, use the query
    parameters `object_id=<@id>` and `object_type=<@type>`
    """

    serializer_class = RawDataSerializer

    def get_queryset(self):
        object_id = self.request.query_params.get('object_id', None)
        object_type = self.request.query_params.get('object_type', None)
        if object_id and object_type:
            return RawData.objects.filter(
                normalizeddata__changeset__changes__target_id=object_id,
                normalizeddata__changeset__changes__target_type__model=object_type
            ).distinct('id')
        else:
            return RawData.objects.all()


class SchemaView(views.APIView):
    """
    Schema used to validate changes or additions to the SHARE dataset.

    To submit changes, see [`/api/normalizeddata`](/api/normalizeddata)

    ## Model schemas
    Each node in the submitted `@graph` is validated by a model schema determined by its `@type`.

    ### Work types
    - [Publication](/api/schema/Publication)
    - [Project](/api/schema/Project)
    - [Preprint](/api/schema/Preprint)
    - [Registration](/api/schema/Registration)
    - [Manuscript](/api/schema/Manuscript)
    - [CreativeWork](/api/schema/CreativeWork)

    ### People
    - [Person](/api/schema/Person)

    ### Entities
    - [Institution](/api/schema/Institution)
    - [Publisher](/api/schema/Publisher)
    - [Funder](/api/schema/Funder)
    - [Organization](/api/schema/Organization)

    ### Other
    - [Award](/api/schema/Award)
    - [Email](/api/schema/Email)
    - [Identifier](/api/schema/Identifier)
    - [Link](/api/schema/Link)
    - [Subject](/api/schema/Subject)
    - [Tag](/api/schema/Tag)
    - [Venue](/api/schema/Venue)

    ### Relationships between nodes
    - [Affiliation](/api/schema/Affiliation)
    - [Association](/api/schema/Association)
    - [Contributor](/api/schema/Contributor)
    - [PersonEmail](/api/schema/PersonEmail)
    - [ThroughAwardEntities](/api/schema/ThroughAwardEntities)
    - [ThroughAwards](/api/schema/ThroughAwards)
    - [ThroughIdentifiers](/api/schema/ThroughIdentifiers)
    - [ThroughLinks](/api/schema/ThroughLinks)
    - [ThroughSubjects](/api/schema/ThroughSubjects)
    - [ThroughTags](/api/schema/ThroughTags)
    - [ThroughVenues](/api/schema/ThroughVenues)
    """
    def get(self, request, *args, **kwargs):
        schema = JSONLDValidator.jsonld_schema.schema
        return Response(schema)


class ModelSchemaView(views.APIView):
    """
    Schema used to validate submitted changes of matching `@type`. See [`/api/schema`](/api/schema)
    """
    def get(self, request, *args, **kwargs):
        model = apps.get_model('share', kwargs['model'])
        schema = JSONLDValidator().validator_for(model).schema
        return Response(schema)


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
    serializer_class = NormalizedDataSerializer
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

            raw = RawData.objects.store_data(doc_id, Harvester.encode_json(self, prelim_data), request.user, app_label)

        # normalize data
        normalized_data = V1Normalizer({}).normalize(raw.data)
        data = {}
        data['data'] = normalized_data
        serializer = NormalizedDataSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            nm_instance = serializer.save()
            async_result = MakeJsonPatches().delay(nm_instance.id, request.user.id)
            return Response({'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'errors': serializer.errors, 'data': prelim_data}, status=status.HTTP_400_BAD_REQUEST)
