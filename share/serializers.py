from rest_framework import serializers

from api import fields
from share import models

class BaseShareSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        # super hates my additional kwarg
        sparse = kwargs.pop('sparse', False)
        super(BaseShareSerializer, self).__init__(*args, **kwargs)
        # remove version fields
        # easier than specifying excludes for every model serializer

        for k, v in tuple(self.fields.items()):
            if sparse or 'version' in k:
                # if they asked for sparse remove all fields but
                # the @id and @type

                # if the field has version, kill it too.
                self.fields.pop(k)

        # remove typedmodel nonsense
        if 'type' in self.fields.keys():
            self.fields.pop('type')

        # add fields with improper names
        self.fields.update({
            '@id': serializers.HyperlinkedIdentityField(
                # view-name: person-detail
                'api:{}-detail'.format(self.Meta.model._meta.model_name),
                lookup_field='pk'
            ),
            '@type': fields.TypeField(),
        })
    class Meta:
        exclude = ('change', 'id')

class VenueSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Venue

class OrganizationSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Organization


class InstitutionSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Institution


class PersonEmailSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.PersonEmail


class IdentifierSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Identifier


class PersonSerializer(BaseShareSerializer):
    # no emails on purpose
    identifiers = IdentifierSerializer(many=True)
    affiliations = OrganizationSerializer(sparse=True, many=True)
    class Meta(BaseShareSerializer.Meta):
        model = models.Person


class AffiliationSerializer(BaseShareSerializer):
    person = PersonSerializer(sparse=True)
    organization = OrganizationSerializer(sparse=True)

    class Meta(BaseShareSerializer.Meta):
        models = models.Affiliation


class ContributorSerializer(BaseShareSerializer):
    person = PersonSerializer()
    cited_name = serializers.ReadOnlyField(source='contributor.cited_name')
    order_cited = serializers.ReadOnlyField(source='contributor.order_cited')
    url = serializers.ReadOnlyField(source='contributor.url')
    # TODO find a way to do this, or don't
    # creative_work = CreativeWorkSerializer(sparse=True)
    class Meta(BaseShareSerializer.Meta):
        model = models.Contributor


class FunderSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Funder


class AwardSerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Award


class TaxonomySerializer(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Taxonomy


class TagSerializer(BaseShareSerializer):
    taxonomy = TaxonomySerializer()
    class Meta(BaseShareSerializer.Meta):
        model = models.Tag


class AbstractCreativeWorkSerializer(BaseShareSerializer):
    tags = TagSerializer(many=True)
    contributors = ContributorSerializer(source='contributor_set', many=True)
    institutions = InstitutionSerializer(sparse=True, many=True)
    venues = VenueSerializer(sparse=True, many=True)
    awards = AwardSerializer(sparse=True, many=True)
    subject = TagSerializer(sparse=True)


class CreativeWorkSerializer(AbstractCreativeWorkSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.CreativeWork


class PreprintSerializer(AbstractCreativeWorkSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Preprint


class ManuscriptSerializer(AbstractCreativeWorkSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Manuscript


class Link(BaseShareSerializer):
    class Meta(BaseShareSerializer.Meta):
        model = models.Link
