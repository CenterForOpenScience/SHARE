from rest_framework.generics import ListCreateAPIView
from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework import permissions

from api.serializers import RawDataSerializer, NormalizedManuscriptSerializer
from share.models import NormalizedManuscript, RawData


class AcceptNormalizedManuscript(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    serializer_class = NormalizedManuscriptSerializer
    required_scopes = ['upload_normalized_manuscript', ]
    queryset = NormalizedManuscript.objects.all()

class AcceptRawData(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    serializer_class = RawDataSerializer
    required_scopes = ['upload_raw_data', ]
    queryset = RawData.objects.all()
