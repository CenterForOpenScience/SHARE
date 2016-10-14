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


class AbstractEntitySerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractEntity


class OrganizationSerializer(AbstractEntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractEntitySerializer.Meta):
        model = models.Organization


class InstitutionSerializer(AbstractEntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractEntitySerializer.Meta):
        model = models.Institution


class PersonSerializer(AbstractEntitySerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractEntitySerializer.Meta):
        model = models.Person


class VenueSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.Venue


class WorkIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.WorkIdentifier


class EntityIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.EntityIdentifier


class ContributionSerializer(BaseShareSerializer):
    entity = AbstractEntitySerializer(sparse=True)
    cited_name = serializers.ReadOnlyField(source='contribution.cited_name')
    order_cited = serializers.ReadOnlyField(source='contribution.order_cited')
    extra = ExtraDataSerializer()
    # TODO find a way to do this, or don't
    # creative_work = CreativeWorkSerializer(sparse=True)

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractContribution
        exclude = ('creative_work',)


class AwardSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

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
    subjects = SubjectSerializer(many=True)
    tags = TagSerializer(many=True)
    venues = VenueSerializer(sparse=True, many=True)

    contributors = ContributionSerializer(source='contribution_set', many=True)

    identifiers = WorkIdentifierSerializer(source='creativeworkidentifiers', many=True)
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


# TODO relation types
class WorkRelationSerializer(BaseShareSerializer):
    from_work = AbstractCreativeWorkSerializer(sparse=True)
    to_work = AbstractCreativeWorkSerializer(sparse=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractWorkRelation


class EntityRelationSerializer(BaseShareSerializer):
    from_work = AbstractEntitySerializer(sparse=True)
    to_work = AbstractEntitySerializer(sparse=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractEntityRelation
