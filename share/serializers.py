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
            if 'version' in k:
                self.fields.pop(k)
            elif sparse:
                # if they asked for sparse remove all fields but
                # the @id and @type
                self.fields.pop(k)

        # add fields with improper names
        self.fields.update({
            '@id': serializers.HyperlinkedIdentityField(
                # view-name: person-detail
                'api:{}-detail'.format(self.Meta.model._meta.model_name),
                lookup_field='pk'
            ),
            '@type': fields.TypeField(),
        })

class VenueSerializer(BaseShareSerializer):
    class Meta:
        model = models.Venue


class InstitutionSerializer(BaseShareSerializer):
    class Meta:
        model = models.Institution


class PersonEmailSerializer(BaseShareSerializer):
    class Meta:
        model = models.PersonEmail


class IdentifierSerializer(BaseShareSerializer):
    class Meta:
        model = models.Identifier


class PersonSerializer(BaseShareSerializer):
    # emails = PersonEmailSerializer(many=True)
    # identifiers = IdentifierSerializer(many=True)
    class Meta:
        model = models.Person


class ContributorSerializer(BaseShareSerializer):
    person = PersonSerializer()
    cited_name = serializers.ReadOnlyField(source='contributor.cited_name')
    order_cited = serializers.ReadOnlyField(source='contributor.order_cited')
    url = serializers.ReadOnlyField(source='contributor.url')
    class Meta:
        model = models.Contributor


class FunderSerializer(BaseShareSerializer):
    class Meta:
        model = models.Funder


class AwardSerializer(BaseShareSerializer):
    class Meta:
        model = models.Award


class TaxonomySerializer(BaseShareSerializer):
    class Meta:
        model = models.Taxonomy


class TagSerializer(BaseShareSerializer):
    taxonomy = TaxonomySerializer()
    class Meta:
        model = models.Tag


class AbstractCreativeWorkSerializer(BaseShareSerializer):
    tags = TagSerializer(many=True)
    contributors = ContributorSerializer(source='contributor_set', many=True)
    institutions = InstitutionSerializer(sparse=True, many=True)


class CreativeWorkSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.CreativeWork


class PreprintSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.Preprint


class ManuscriptSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.Manuscript


class Link(BaseShareSerializer):
    class Meta:
        model = models.Link
