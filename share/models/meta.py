from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, URIField
from share.apps import ShareConfig as share_config


__all__ = ('Venue', 'Award', 'Tag', 'Link')

# TODO Rename this file


class Venue(ShareObject):
    name = models.CharField(max_length=255)
    venue_type = models.URLField(blank=True)
    location = models.URLField(blank=True)
    community_identifier = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    award = models.URLField(blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.description


class Tag(ShareObject):
    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Link(ShareObject):
    url = URIField()
    type = models.IntegerField(choices=share_config.link_type_choices)
    work = ShareForeignKey('AbstractCreativeWork')

    def __str__(self):
        return self.url


# Through Tables for all the things

class ThroughLinks(ShareObject):
    link = ShareForeignKey(Link)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughVenues(ShareObject):
    venue = ShareForeignKey(Venue)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughAwards(ShareObject):
    award = ShareForeignKey(Award)
    creative_work = ShareForeignKey('AbstractCreativeWork')


class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag)
    creative_work = ShareForeignKey('AbstractCreativeWork')
