from django.db import models

from share.models.base import ShareObject
from share.models.contributor import Person
from share.models.base import TypedShareObjectMeta
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Tag
from share.models.fields import ShareForeignKey, ShareManyToManyField


class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField()
    description = models.TextField()
    contributors = ShareManyToManyField(Person, through='Contributor')
    institutions = ShareManyToManyField(Institution, through='Institution')
    venues = ShareManyToManyField(Venue, through='Venue')
    funders = ShareManyToManyField(Funder, through='Funder')
    awards = ShareManyToManyField(Award, through='Award')
    data_providers = ShareManyToManyField(DataProvider, through='DataProvider')
    provider_link = models.URLField(blank=True)
    subject = ShareForeignKey(Tag, related_name='subjected')
    # TODO: eventually we should try and make that blank=False
    doi = models.URLField(blank=True)
    isbn = models.URLField(blank=True)
    tags = ShareManyToManyField(Tag, related_name='tagged', through='Tag')
    # TODO: We should probably figure out what this means, I don't know
    work_type = models.URLField(blank=True)
    created = models.DateTimeField(null=True)
    published = models.DateTimeField(null=True)
    free_to_read_type = models.URLField(blank=True)
    free_to_read_date = models.DateTimeField(null=True)
    license = models.URLField(blank=True)

class CreativeWork(AbstractCreativeWork):
    pass
