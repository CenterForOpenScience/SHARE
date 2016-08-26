from rest_framework import viewsets, views, status
from rest_framework.response import Response

from api.filters import ChangeSetFilterSet, ChangeFilterSet
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.serializers import NormalizedDataSerializer, ChangeSetSerializer, ChangeSerializer, RawDataSerializer, \
    ShareUserSerializer, ProviderSerializer
from share.models import ChangeSet, Change, RawData, ShareUser, NormalizedData
from share.models.validators import JSONLDValidator
from share.tasks import MakeJsonPatches

__all__ = ('NormalizedDataViewSet', 'ChangeSetViewSet', 'ChangeViewSet', 'RawDataViewSet', 'ShareUserViewSet', 'ProviderViewSet', 'SchemaView')


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
                        'normalized_data': {
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
                        'normalized_data': {
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
                        'normalized_data': {
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
        prelim_data = request.data
        prelim_data['source'] = request.user.id
        serializer = NormalizedDataSerializer(data=prelim_data)
        if serializer.is_valid():
            nm_instance = serializer.save()
            async_result = MakeJsonPatches().delay(nm_instance.id, request.user.id)
            return Response({'normalized_id': nm_instance.id, 'task_id': async_result.id}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'errors': serializer.errors, 'data': prelim_data}, status=status.HTTP_400_BAD_REQUEST)


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
    def get(self, request, *args, **kwargs):
        model = kwargs['model']
        schema = JSONLDValidator()
