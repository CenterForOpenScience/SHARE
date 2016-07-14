from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, URIField, ShareURLField, ShareManyToManyField
from share.apps import ShareConfig as share_config


__all__ = ('Venue', 'Award', 'Tag', 'Link')

# TODO Rename this file


class Venue(ShareObject):
    name = models.TextField()
    venue_type = ShareURLField(blank=True)
    location = ShareURLField(blank=True)
    community_identifier = ShareURLField(blank=True)

    def __str__(self):
        return self.name


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    award = ShareURLField(blank=True)
    description = models.TextField(blank=True)
    url = ShareURLField(blank=True)
    funder = ShareManyToManyField('Funder', through='ThroughAwardFunders')

    def __str__(self):
        return self.description


class Tag(ShareObject):
    name = models.TextField(db_index=True)
    url = ShareURLField(blank=True)

    def __str__(self):
        return self.name


class Link(ShareObject):
    url = URIField(db_index=True)
    type = models.TextField(choices=share_config.link_type_choices)

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


class ThroughAwardFunders(ShareObject):
    award = ShareForeignKey('Award')
    funder = ShareForeignKey('Funder')
