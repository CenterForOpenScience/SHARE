from django.db import models

from share.models.base import ShareObject
from share.models.people import Person
from share.models.base import TypedShareObjectMeta
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Tag
from share.models.fields import ShareForeignKey, ShareManyToManyField


class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    contributors = ShareManyToManyField(Person, through='Contributor')
    institutions = ShareManyToManyField(Institution, through='ThroughInstitutions')
    venues = ShareManyToManyField(Venue, through='ThroughVenues')
    funders = ShareManyToManyField(Funder, through='ThroughFunders')
    awards = ShareManyToManyField(Award, through='ThroughAwards')
    data_providers = ShareManyToManyField(DataProvider, through='ThroughDataProviders')
    provider_link = models.URLField(blank=True)
    subject = ShareForeignKey(Tag, related_name='subjected_%(class)s', null=True)
    # TODO: eventually we should try and make that blank=False
    # Note: Null allows inserting of None but returns it as an empty string
    doi = models.URLField(blank=True, null=True)
    isbn = models.URLField(blank=True)
    tags = ShareManyToManyField(Tag, related_name='tagged_%(class)s', through='ThroughTags')
    # TODO: We should probably figure out what this means, I don't know
    work_type = models.URLField(blank=True)
    created = models.DateTimeField(null=True)
    published = models.DateTimeField(null=True)
    free_to_read_type = models.URLField(blank=True)
    free_to_read_date = models.DateTimeField(null=True)

    license = models.URLField(blank=True)
    # rights = models.TextField(blank=True)
    # language = models.TextField(blank=True)


class CreativeWork(AbstractCreativeWork):
    pass
