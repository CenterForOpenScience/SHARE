from rest_framework import views
from rest_framework import viewsets
from rest_framework.response import Response

from api.users.serializers import ShareUserSerializer

from share import models


class ShareUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns details about the currently logged in user
    """
    serializer_class = ShareUserSerializer

    def get_queryset(self):
        return models.ShareUser.objects.filter(pk=self.request.user.pk)


# TODO Remove me
class ShareUserView(views.APIView):
    def get(self, request, *args, **kwargs):
        ser = ShareUserSerializer(request.user, token=True)
        return Response(ser.data)
