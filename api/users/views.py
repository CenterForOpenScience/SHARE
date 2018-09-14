from rest_framework import views
from rest_framework import viewsets
from rest_framework.response import Response

from api.users.serializers import ShareUserSerializer
from api.users.serializers import ShareUserWithTokenSerializer

from share import models


class ShareUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns details about the currently logged in user
    """
    serializer_class = ShareUserSerializer

    def get_queryset(self):
        return models.ShareUser.objects.filter(pk=self.request.user.pk).order_by('-id')


# TODO Remove this when refactoring users endpoints (SHARE-586)
class ShareUserView(views.APIView):
    resource_name = 'ShareUser'

    def get(self, request, *args, **kwargs):
        ser = ShareUserWithTokenSerializer(request.user)
        return Response(ser.data)
