from rest_framework import viewsets, permissions

from api.filters import ShareObjectFilterSet
from share import serializers

class ShareObjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, ]  # TokenHasScope]
    # TODO: Add in scopes once we figure out who, why, and how.
    # required_scopes = ['', ]
    filter_class = ShareObjectFilterSet


class ExtraDataViewSet(ShareObjectViewSet):
    serializer_class = serializers.ExtraDataSerializer
    queryset = serializer_class.Meta.model.objects.all()


class EntityViewSet(ShareObjectViewSet):
    serializer_class = serializers.EntitySerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class VenueViewSet(ShareObjectViewSet):
    serializer_class = serializers.VenueSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class OrganizationViewSet(ShareObjectViewSet):
    serializer_class = serializers.OrganizationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class PublisherViewSet(ShareObjectViewSet):
    serializer_class = serializers.PublisherSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class InstitutionViewSet(ShareObjectViewSet):
    serializer_class = serializers.InstitutionSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class IdentifierViewSet(ShareObjectViewSet):
    serializer_class = serializers.IdentifierSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class PersonViewSet(ShareObjectViewSet):
    serializer_class = serializers.PersonSerializer
    queryset = serializer_class.Meta.model.objects.select_related(
        'extra'
    ).prefetch_related(
        'emails',
        'affiliations',
        'identifiers'
    )


class AffiliationViewSet(ShareObjectViewSet):
    serializer_class = serializers.AffiliationSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra', 'person', 'entity')


class ContributorViewSet(ShareObjectViewSet):
    serializer_class = serializers.ContributorSerializer
    queryset = serializer_class.Meta.model.objects.select_related('extra', 'person', 'creative_work')


class FunderViewSet(ShareObjectViewSet):
    serializer_class = serializers.FunderSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class AwardViewSet(ShareObjectViewSet):
    serializer_class = serializers.AwardSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class TagViewSet(ShareObjectViewSet):
    serializer_class = serializers.TagSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related('extra')


class CreativeWorkViewSet(ShareObjectViewSet):
    serializer_class = serializers.CreativeWorkSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )


class PreprintViewSet(ShareObjectViewSet):
    serializer_class = serializers.PreprintSerializer
    queryset = serializer_class.Meta.model.objects.select_related(
        'subject',
        'extra'
    )


class ManuscriptViewSet(ShareObjectViewSet):
    serializer_class = serializers.ManuscriptSerializer
    queryset = serializer_class.Meta.model.objects.all().select_related(
        'subject',
        'extra'
    )
