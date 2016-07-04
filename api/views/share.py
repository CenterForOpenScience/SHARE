from rest_framework import viewsets, permissions

from api.filters import ShareObjectFilterSet
from share import serializers

class ShareObjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    filter_class = ShareObjectFilterSet

class VenueViewSet(ShareObjectViewSet):
    serializer_class = serializers.VenueSerializer
    queryset = serializer_class.Meta.model.objects.all()


class InstitutionViewSet(ShareObjectViewSet):
    serializer_class = serializers.InstitutionSerializer
    queryset = serializer_class.Meta.model.objects.all()


class FunderViewSet(ShareObjectViewSet):
    serializer_class = serializers.FunderSerializer
    queryset = serializer_class.Meta.model.objects.all()


class AwardViewSet(ShareObjectViewSet):
    serializer_class = serializers.AwardSerializer
    queryset = serializer_class.Meta.model.objects.all()


class TagViewSet(ShareObjectViewSet):
    serializer_class = serializers.TagSerializer
    queryset = serializer_class.Meta.model.objects.all()


class CreativeWorkViewSet(ShareObjectViewSet):
    serializer_class = serializers.CreativeWorkSerializer
    queryset = serializer_class.Meta.model.objects.all()


class PreprintViewSet(ShareObjectViewSet):
    serializer_class = serializers.PreprintSerializer
    queryset = serializer_class.Meta.model.objects.all()


class ManuscriptViewSet(ShareObjectViewSet):
    serializer_class = serializers.ManuscriptSerializer
    queryset = serializer_class.Meta.model.objects.all()


class PersonViewSet(ShareObjectViewSet):
    serializer_class = serializers.PersonSerializer
    queryset = serializer_class.Meta.model.objects.all()

class ContributorViewSet(ShareObjectViewSet):
    serializer_class = serializers.ContributorSerializer
    queryset = serializer_class.Meta.model.objects.all()
