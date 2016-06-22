from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey

__all__ = ('Person', 'Email', 'PersonEmail', 'Contributor', 'Manuscript', 'Affiliation', 'Organization')


# ShareObject = models.Model
# ShareForeignKey = models.ForeignKey

class Organization(ShareObject):
    name = models.CharField(max_length=200)
    # parent = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)


class Email(ShareObject):
    is_primary = models.BooleanField()
    email = models.EmailField()

    def __str__(self):
        return self.email



class Person(ShareObject):
    family_name = models.CharField(max_length=200)  # last
    given_name = models.CharField(max_length=200)  # first
    additional_name = models.CharField(max_length=200, blank=True)  # can be used for middle
    suffix = models.CharField(max_length=50, blank=True)

    emails = models.ManyToManyField(Email, through='PersonEmail')
    affiliations = models.ManyToManyField(Organization, through='Affiliation')

    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle


class Affiliation(ShareObject):
    # start_date = models.DateField()
    # end_date = models.DateField()
    person = ShareForeignKey(Person)
    organization = ShareForeignKey(Organization)

    def __str__(self):
        return self.organization.name


class PersonEmail(ShareObject):
    email = ShareForeignKey(Email)
    person = ShareForeignKey(Person)


class Manuscript(ShareObject):
    title = models.TextField()
    description = models.TextField()
    contributors = models.ManyToManyField(Person, through='Contributor')


class Contributor(ShareObject):
    person = ShareForeignKey(Person)
    manuscript = ShareForeignKey(Manuscript)
