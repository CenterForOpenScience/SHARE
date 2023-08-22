import jsonschema

from django.db import transaction

from rest_framework import views, status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from trove import digestive_tract

from api import v1_schemas
from api.authentication import APIV1TokenBackPortAuthentication
from api.deprecation import deprecate
from api.permissions import ReadOnlyOrTokenHasScopeOrIsAuthenticated
from api.normalizeddata.serializers import BasicNormalizedDataSerializer


__all__ = ('V1DataView', )


@deprecate(pls_hide=False)
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
    permission_classes = (ReadOnlyOrTokenHasScopeOrIsAuthenticated, )
    serializer_class = BasicNormalizedDataSerializer
    renderer_classes = (JSONRenderer, )
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):

        try:
            jsonschema.validate(request.data, v1_schemas.v1_push_schema)
        except (jsonschema.exceptions.ValidationError) as error:
            raise ParseError(detail=error.message)

        try:
            prelim_data = request.data['jsonData']
        except ParseError as error:
            return Response(
                'Invalid JSON - {0}'.format(error.message),
                status=status.HTTP_400_BAD_REQUEST
            )

        # store raw data, assuming you can only submit one at a time
        with transaction.atomic():
            try:
                doc_id = prelim_data['uris']['canonicalUri']
            except KeyError:
                return Response({'errors': 'Canonical URI not found in uris.', 'data': prelim_data}, status=status.HTTP_400_BAD_REQUEST)

            _task_id = digestive_tract.swallow__sharev2_legacy(
                from_user=request.user,
                record=prelim_data,
                record_identifier=doc_id,
                transformer_key='v1_push',
                urgent=True,
            )
            return Response({
                'task_id': _task_id,
            }, status=status.HTTP_202_ACCEPTED)
