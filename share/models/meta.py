from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, URIField
from share.apps import ShareConfig as share_config


__all__ = ('Venue', 'Award', 'Taxonomy', 'Tag', 'Link')

# TODO Rename this file


class Venue(ShareObject):
    name = models.CharField(max_length=255)
    venue_type = models.URLField(blank=True)
    location = models.URLField(blank=True)
    community_identifier = models.URLField(blank=True)


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    award = models.URLField(blank=True)
    description = models.TextField(blank=True)
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
    type = ShareForeignKey(Taxonomy, null=True)


class Link(ShareObject):
    # TODO Make this A URN Field that isn't stupid
    url = URIField()
    type = models.IntegerField(choices=share_config.link_type_choices)
    work = ShareForeignKey('AbstractCreativeWork')


# Through Tables for all the things

class ThroughVenues(ShareObject):
    venue = ShareForeignKey(Venue)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughAwards(ShareObject):
    award = ShareForeignKey(Award)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag)
    creative_work = ShareForeignKey('AbstractCreativeWork')
