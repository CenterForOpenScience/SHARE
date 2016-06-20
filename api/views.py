from rest_framework.generics import CreateAPIView
from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import permissions

from api.serializers import RawDataSerializer, NormalizedManuscriptSerializer


class AcceptNormalizedManuscript(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    serializer_class = NormalizedManuscriptSerializer
    required_scopes = ['upload_normalized_manuscript', ]



class AcceptRawData(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    serializer_class = RawDataSerializer
    required_scopes = ['upload_raw_data', ]
