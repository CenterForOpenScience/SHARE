from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField


__all__ = ('Entity', 'Funder', 'Organization', 'Publisher', 'Institution')


class Entity(ShareObject, metaclass=TypedShareObjectMeta):
    url = models.URLField(blank=True)
    name = models.TextField()
    location = models.TextField(blank=True)
    affiliations = ShareManyToManyField('Person', through='Affiliation')

    class Meta:
        verbose_name_plural = 'Entities'


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
    ringgold = models.URLField(blank=True)
