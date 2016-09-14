from rest_framework import serializers

from django.apps import apps

from api import fields
from share import models


class BaseShareSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        # super hates my additional kwargs
        sparse = kwargs.pop('sparse', False)
        version_serializer = kwargs.pop('version_serializer', False)
        super(BaseShareSerializer, self).__init__(*args, **kwargs)

        if sparse:
            # clear the fields if they asked for sparse
            self.fields.clear()
            self.fields['id'] = serializers.IntegerField()

        else:
            # remove hidden fields
            excluded_fields = ['change', 'uuid', 'sources']
            for field_name in tuple(self.fields.keys()):
                if 'version' in field_name or field_name in excluded_fields:
                    self.fields.pop(field_name)

        # version specific fields
        if version_serializer:
            self.fields.update({
                'action': serializers.CharField(max_length=10),
                'persistent_id': serializers.IntegerField()
            })

        # add fields with improper names
        self.fields.update({
            '@id': serializers.HyperlinkedIdentityField(
                # view-name: person-detail
                'api:{}-detail'.format(self.Meta.model._meta.model_name),
                lookup_field='pk'
            ),
            '@type': fields.TypeField(),
            'type': fields.TypeField(),
            'object_id': fields.ObjectIDField(source='uuid'),
        })

    class Meta:
        pass


class ExtraDataSerializer(BaseShareSerializer):
    data = serializers.JSONField()

    class Meta(BaseShareSerializer.Meta):
        model = models.ExtraData


class EntitySerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Entity


class VenueSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Venue


class RelationSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()
    link_type = serializers.CharField(source='type')

    class Meta(BaseShareSerializer.Meta):
        model = models.Relation


class OrganizationSerializer(EntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(EntitySerializer.Meta):
        model = models.Organization


class PublisherSerializer(EntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(EntitySerializer.Meta):
        model = models.Publisher


class InstitutionSerializer(EntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(EntitySerializer.Meta):
        model = models.Institution


class PersonEmailSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.PersonEmail


class IdentifierSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Identifier


class PersonSerializer(BaseShareSerializer):
    # no emails on purpose
    identifiers = IdentifierSerializer(sparse=True, many=True)
    affiliations = OrganizationSerializer(sparse=True, many=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Person
        exclude = ('emails',)


class AffiliationSerializer(BaseShareSerializer):
    person = PersonSerializer(sparse=True)
    organization = OrganizationSerializer(sparse=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Affiliation


class ContributorSerializer(BaseShareSerializer):
    person = PersonSerializer()
    cited_name = serializers.ReadOnlyField(source='contributor.cited_name')
    order_cited = serializers.ReadOnlyField(source='contributor.order_cited')
    url = serializers.ReadOnlyField(source='contributor.url')
    extra = ExtraDataSerializer()
    # TODO find a way to do this, or don't
    # creative_work = CreativeWorkSerializer(sparse=True)

    class Meta(BaseShareSerializer.Meta):
        model = models.Contributor
        exclude = ('creative_work',)


class FunderSerializer(EntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(EntitySerializer.Meta):
        model = models.Funder


class AwardSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()
    entities = EntitySerializer(many=True)

    class Meta(BaseShareSerializer.Meta):
        model = models.Award


class TagSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Tag


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = ('id', 'name', 'lineages')


class AbstractCreativeWorkSerializer(BaseShareSerializer):
    tags = TagSerializer(many=True)
    contributors = ContributorSerializer(source='contributor_set', many=True)
    institutions = InstitutionSerializer(sparse=True, many=True)
    organizations = OrganizationSerializer(sparse=True, many=True)
    publishers = PublisherSerializer(sparse=True, many=True)
    funders = FunderSerializer(sparse=True, many=True)
    venues = VenueSerializer(sparse=True, many=True)
    awards = AwardSerializer(sparse=True, many=True)
    identifiers = IdentifierSerializer(many=True)
    relations = RelationSerializer(many=True)
    subjects = SubjectSerializer(many=True)
    extra = ExtraDataSerializer()


def make_creative_work_serializer_class(model):
    if isinstance(model, str):
        model = apps.get_model('share', model)

    class CreativeWorkSerializer(AbstractCreativeWorkSerializer):
        class Meta(BaseShareSerializer.Meta):
            model = None

    CreativeWorkSerializer.Meta.model = model
    return CreativeWorkSerializer
