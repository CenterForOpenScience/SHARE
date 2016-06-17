from rest_framework.response import Response
from rest_framework.views import APIView
from oauth2_provider.ext.rest_framework import TokenHasReadWriteScope, TokenHasScope
from rest_framework import permissions


class AcceptNormalizedManuscript(APIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]

    def post(self, request, format=None):
        print(request.body)
        return Response('{} -- woot!'.format(request.body))

