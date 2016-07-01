from rest_framework import serializers
from share import models


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Venue


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Institution


class PersonEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PersonEmail


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Identifier


class PersonSerializer(serializers.ModelSerializer):
    emails = PersonEmailSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)
    class Meta:
        model = models.Person


class ContributorSerializer(serializers.ModelSerializer):
    person = PersonSerializer()
    class Meta:
        model = models.Contributor


class FunderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Funder


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Award


class DataProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DataProvider


class TaxonomySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Taxonomy


class TagSerializer(serializers.ModelSerializer):
    taxonomy = TaxonomySerializer()
    class Meta:
        model = models.Tag


class AbstractCreativeWorkSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)


class CreativeWorkSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.CreativeWork


class PreprintSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.Preprint


class ManuscriptSerializer(AbstractCreativeWorkSerializer):
    class Meta:
        model = models.Manuscript


class Link(serializers.ModelSerializer):
    class Meta:
        model = models.Link
