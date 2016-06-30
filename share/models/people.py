from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareManyToManyField

__all__ = ('Person', 'Email', 'PersonEmail', 'Affiliation', 'Organization')


class Organization(ShareObject):
    name = models.CharField(max_length=200)
    # parent = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)


class Email(ShareObject):
    is_primary = models.BooleanField()
    email = models.EmailField()

    def __str__(self):
        return self.email


class Identifier(ShareObject):
    # https://twitter.com/berniethoughts/
    url = models.URLField()
    # https://twitter.com/
    base_url = models.URLField()


class Person(ShareObject):
    family_name = models.CharField(max_length=200)  # last
    given_name = models.CharField(max_length=200)  # first
    additional_name = models.CharField(max_length=200, blank=True)  # can be used for middle
    suffix = models.CharField(max_length=50, blank=True)

    emails = ShareManyToManyField(Email, through='PersonEmail')
    affiliations = ShareManyToManyField(Organization, through='Affiliation')
    orcid = models.URLField(blank=True)
    # this replaces "authority_id" and "other_identifiers" in the diagram
    identifiers = ShareManyToManyField(Identifier, through='ThroughIdentifiers')
    location = models.URLField(blank=True)
    url = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = 'People'

    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle


class PersonEmail(ShareObject):
    email = ShareForeignKey(Email)
    person = ShareForeignKey(Person)


class Affiliation(ShareObject):
    # start_date = models.DateField()
    # end_date = models.DateField()
    person = ShareForeignKey(Person)
    organization = ShareForeignKey(Organization)

    def __str__(self):
        return self.organization.name
