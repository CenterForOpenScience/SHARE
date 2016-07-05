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
    queryset = serializer_class.Meta.model.objects.all()


class VenueViewSet(ShareObjectViewSet):
    serializer_class = serializers.VenueSerializer
    queryset = serializer_class.Meta.model.objects.all()


class OrganizationViewSet(ShareObjectViewSet):
    serializer_class = serializers.OrganizationSerializer
    queryset = serializer_class.Meta.model.objects.all()


class PublisherViewSet(ShareObjectViewSet):
    serializer_class = serializers.PublisherSerializer
    queryset = serializer_class.Meta.model.objects.all()


class InstitutionViewSet(ShareObjectViewSet):
    serializer_class = serializers.InstitutionSerializer
    queryset = serializer_class.Meta.model.objects.all()


class IdentifierViewSet(ShareObjectViewSet):
    serializer_class = serializers.IdentifierSerializer
    queryset = serializer_class.Meta.model.objects.all()


class PersonViewSet(ShareObjectViewSet):
    serializer_class = serializers.PersonSerializer
    queryset = serializer_class.Meta.model.objects.prefetch_related('emails', 'affiliations', 'identifiers')


class AffiliationViewSet(ShareObjectViewSet):
    serializer_class = serializers.AffiliationSerializer
    queryset = serializer_class.Meta.model.objects.all()


class ContributorViewSet(ShareObjectViewSet):
    serializer_class = serializers.ContributorSerializer
    queryset = serializer_class.Meta.model.objects.select_related('person')


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
    queryset = serializer_class.Meta.model.objects.select_related(
        'subject'
    ).prefetch_related(
            'contributors',
            'awards',
            'venues',
            'links',
            'funders',
            'publishers',
            'institutions',
            'tags'
    )


class ManuscriptViewSet(ShareObjectViewSet):
    serializer_class = serializers.ManuscriptSerializer
    queryset = serializer_class.Meta.model.objects.all()
