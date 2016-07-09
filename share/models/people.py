from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareManyToManyField

__all__ = ('Person', 'Email', 'PersonEmail', 'Affiliation', 'Identifier', 'Contributor')


# Person Auxillary classes

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


# Actual Person

class Person(ShareObject):
    family_name = models.TextField()  # last
    given_name = models.TextField()  # first
    additional_name = models.TextField(blank=True)  # can be used for middle
    suffix = models.TextField(blank=True)

    emails = ShareManyToManyField(Email, through='PersonEmail')
    affiliations = ShareManyToManyField('Entity', through='Affiliation')
    # this replaces "authority_id" and "other_identifiers" in the diagram
    identifiers = ShareManyToManyField(Identifier, through='ThroughIdentifiers')
    location = models.TextField(blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return ' '.join(x for x in [self.given_name, self.family_name, self.additional_name, self.suffix] if x)

    class Meta:
        verbose_name_plural = 'People'

    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle


# Through Tables for Person

class ThroughIdentifiers(ShareObject):
    person = ShareForeignKey(Person)
    identifier = ShareForeignKey(Identifier)


class PersonEmail(ShareObject):
    email = ShareForeignKey(Email)
    person = ShareForeignKey(Person)


class Affiliation(ShareObject):
    # start_date = models.DateField()
    # end_date = models.DateField()
    person = ShareForeignKey(Person)
    entity = ShareForeignKey('Entity')

    def __str__(self):
        return '{} ({})'.format(self.person, self.entity)


class Contributor(ShareObject):
    cited_name = models.TextField(blank=True)
    order_cited = models.PositiveIntegerField(null=True)

    person = ShareForeignKey(Person)
    creative_work = ShareForeignKey('AbstractCreativeWork')

    def __str__(self):
        return '{} -> {}'.format(self.person, self.creative_work)
