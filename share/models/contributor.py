from django.db import models

from share.models.base import ShareObject
from share.models.base import ShareForeignKey


class Organization(models.Model):
    name = models.CharField(max_length=200)
    # parent = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)


class Email(ShareObject):
    is_primary = models.BooleanField()
    email = models.EmailField()

    def __str__(self):
        return self.email


class Affiliation(ShareObject):

    start_date = models.DateField()
    end_date = models.DateField()
    # organization = ShareForeignKey(Organization, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.organization.name


class Person(ShareObject):
    family_name = models.CharField(max_length=200)  # last
    given_name = models.CharField(max_length=200)  # first
    additional_name = models.CharField(max_length=200, blank=True)  # can be used for middle
    suffix = models.CharField(max_length=50, blank=True)
    emails = models.ManyToManyField(Email, through='PersonEmail')

    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle


class PersonEmail(ShareObject):
    email = ShareForeignKey(Email)
    person = ShareForeignKey(Person)
