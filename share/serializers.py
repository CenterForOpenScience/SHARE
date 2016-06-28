from rest_framework import serializers
from share import models


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Venue


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Institution


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
    class Meta:
        model = models.Tag


class CreativeWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CreativeWork


class PreprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Preprint


class ManuscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Manuscript
