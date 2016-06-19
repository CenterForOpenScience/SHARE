from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import permissions


class AcceptNormalizedManuscript(APIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]

    required_scopes = ['upload_normalized_manuscript', ]

    def post(self, request, format=None):
        # import ipdb; ipdb.set_trace()
        # validate data as JSON-LD

        return Response()


class AcceptRawData(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    serializer_class = RawDataSerializer
    required_scopes = ['upload_raw_manuscript', ]
