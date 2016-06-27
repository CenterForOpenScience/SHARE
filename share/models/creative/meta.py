from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey


class Venue(ShareObject):
    name = models.CharField(max_length=255)
    venue_type = models.URLField(blank=True)
    location = models.URLField(blank=True)
    community_identifier = models.URLField(blank=True)


class Institution(ShareObject):
    # TODO: ScholarlyArticle says this should be an Organization
    name = models.CharField(max_length=255)
    isni = models.URLField(blank=True)
    rinngold = models.URLField(blank=True)
    location = models.URLField(blank=True)
    url = models.URLField(blank=True)


class Funder(ShareObject):
    # TODO: ScholarlyArticle says this should be a DiscourseElement
    # http://purl.org/spar/deo/DiscourseElement
    # many fields are missing but seem extraneous to our purpose
    funder_name = models.CharField(max_length=255)
    funder_region = models.URLField(blank=True)
    community_identifier = models.URLField(blank=True)
    url = models.URLField(blank=True)


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    award = models.URLField(blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)


class DataProvider(ShareObject):
    name = models.CharField(max_length=255)
    location = models.URLField(blank=True)
    community_id = models.URLField(blank=True)
    url = models.URLField(blank=True)


class Taxonomy(ShareObject):
    # eventually, this can be good, pointing to a taxonomy url
    # for now, it can keep a separate list of tags by provider
    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)


class Tag(ShareObject):
    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    # this is here to force disambiguation between providers' tags
    type = ShareForeignKey(Taxonomy)
