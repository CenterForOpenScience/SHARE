from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta


__all__ = ('Entity', 'Funder', 'Organization', 'Publisher', 'Institution')


class Entity(ShareObject, metaclass=TypedShareObjectMeta):
    url = models.URLField(blank=True)
    name = models.CharField(max_length=255)
    # TODO Expand to geolocation or text field for address
    location = models.URLField(blank=True)


class Funder(Entity):
    # TODO: ScholarlyArticle says this should be a DiscourseElement
    # http://purl.org/spar/deo/DiscourseElement
    # many fields are missing but seem extraneous to our purpose
    funder_region = models.URLField(blank=True)
    community_identifier = models.URLField(blank=True)


class Organization(Entity):
    pass


class Publisher(Entity):
    pass


class Institution(Entity):
    # TODO: ScholarlyArticle says this should be an Organization
    isni = models.URLField(blank=True)
    rinngold = models.URLField(blank=True)
