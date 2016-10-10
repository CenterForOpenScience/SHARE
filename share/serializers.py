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
        else:
            # remove hidden fields
            excluded_fields = ['change', 'uuid', 'sources']
            for field_name in tuple(self.fields.keys()):
                if 'version' in field_name or field_name in excluded_fields:
                    self.fields.pop(field_name)

            if not version_serializer:
                # add links to related objects
                self.fields.update({
                    'links': fields.LinksField(links=self.Meta.links, source='*')
                })

        # version specific fields
        if version_serializer:
            self.fields.update({
                'action': serializers.CharField(max_length=10),
                'persistent_id': serializers.IntegerField()
            })

        # add fields with improper names
        self.fields.update({
            '@id': fields.DetailUrlField(),
            '@type': fields.TypeField(),
            # TODO make ember-share understand @tributes and remove these
            'id': serializers.IntegerField(),
            'type': fields.TypeField(),
        })

    class Meta:
        links = ('versions', 'changes', 'rawdata')


class ExtraDataSerializer(BaseShareSerializer):
    data = serializers.JSONField()

    class Meta(BaseShareSerializer.Meta):
        links = ()
        model = models.ExtraData


class EntitySerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Entity


class VenueSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Venue


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


class CreativeWorkIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.CreativeWorkIdentifier


class PersonIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.PersonIdentifier


class PersonSerializer(BaseShareSerializer):
    # no emails on purpose
    personidentifiers = PersonIdentifierSerializer(many=True)
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
    creativeworkidentifiers = CreativeWorkIdentifierSerializer(many=True)
    subjects = SubjectSerializer(many=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractCreativeWork
        links = ('versions', 'changes', 'rawdata', 'relations')


def make_creative_work_serializer_class(model):
    if isinstance(model, str):
        model = apps.get_model('share', model)

    class CreativeWorkSerializer(AbstractCreativeWorkSerializer):
        class Meta(AbstractCreativeWorkSerializer.Meta):
            pass

    CreativeWorkSerializer.Meta.model = model
    return CreativeWorkSerializer


class RelationSerializer(BaseShareSerializer):
    from_work = AbstractCreativeWorkSerializer(sparse=True)
    to_work = AbstractCreativeWorkSerializer(sparse=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Relation
