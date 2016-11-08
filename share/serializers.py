from collections import OrderedDict

from rest_framework_json_api import serializers

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
            'type': fields.TypeField(),
        })

    class Meta:
        links = ('versions', 'changes', 'rawdata')

    # http://stackoverflow.com/questions/27015931/remove-null-fields-from-django-rest-framework-response
    def to_representation(self, instance):
        def not_none(value):
            return value is not None

        ret = super(BaseShareSerializer, self).to_representation(instance)
        ret = OrderedDict(list(filter(lambda x: not_none(x[1]), ret.items())))
        return ret


class ExtraDataSerializer(BaseShareSerializer):
    data = serializers.JSONField()

    class Meta(BaseShareSerializer.Meta):
        links = ()
        model = models.ExtraData


class AbstractAgentSerializer(BaseShareSerializer):
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractAgent


class OrganizationSerializer(AbstractAgentSerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractAgentSerializer.Meta):
        model = models.Organization


class InstitutionSerializer(AbstractAgentSerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractAgentSerializer.Meta):
        model = models.Institution


class PersonSerializer(AbstractAgentSerializer):
    extra = ExtraDataSerializer()

    class Meta(AbstractAgentSerializer.Meta):
        model = models.Person


class WorkIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.WorkIdentifier


class AgentIdentifierSerializer(BaseShareSerializer):
    # TODO filter/obfuscate mailto identifiers
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AgentIdentifier


# class ContributionSerializer(BaseShareSerializer):
#     agent = AbstractAgentSerializer(sparse=True)
#     cited_name = serializers.ReadOnlyField(source='contribution.cited_name')
#     order_cited = serializers.ReadOnlyField(source='contribution.order_cited')
#     extra = ExtraDataSerializer()
#     # TODO find a way to do this, or don't
#     # creative_work = CreativeWorkSerializer(sparse=True)

#     class Meta(BaseShareSerializer.Meta):
#         model = models.AbstractContribution
#         exclude = ('creative_work',)


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

    # contributors = ContributionSerializer(source='contribution_set', many=True)

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


class AgentRelationSerializer(BaseShareSerializer):
    from_work = AbstractAgentSerializer(sparse=True)
    to_work = AbstractAgentSerializer(sparse=True)
    extra = ExtraDataSerializer()

    class Meta(BaseShareSerializer.Meta):
        model = models.AbstractAgentRelation
