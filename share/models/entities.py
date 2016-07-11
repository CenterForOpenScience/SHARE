from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField, ShareURLField

__all__ = ('Entity', 'Funder', 'Organization', 'Publisher', 'Institution')


class Entity(ShareObject, metaclass=TypedShareObjectMeta):
    url = ShareURLField(blank=True)
    name = models.TextField()
    location = models.TextField(blank=True)
    affiliations = ShareManyToManyField('Person', through='Affiliation')

    class Meta:
        verbose_name_plural = 'Entities'
        index_together = (
            ('type', 'name',)
        )


class Funder(Entity):
    # TODO: ScholarlyArticle says this should be a DiscourseElement
    # http://purl.org/spar/deo/DiscourseElement
    # many fields are missing but seem extraneous to our purpose
    funder_region = ShareURLField(blank=True)
    community_identifier = ShareURLField(blank=True)


class Organization(Entity):
    pass


class Publisher(Entity):
    pass


class Institution(Entity):
    # TODO: ScholarlyArticle says this should be an Organization
    isni = ShareURLField(blank=True)
    ringgold = ShareURLField(blank=True)
