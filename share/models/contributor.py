from django.db import models
from django.contrib.postgres.fields import JSONField

from share.models.base import ShareModel
from share.models.base import ShareManyToMany
from share.models.base import ShareForeignKey


class Organization(models.Model):
    name = models.CharField(max_length=200)
    #parent = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)



class Email(ShareModel):
    is_primary = models.BooleanField()
    email = models.EmailField()

    def __str__(self):
        return self.email


class Affiliation(ShareModel):

    start_date = models.DateField()
    end_date = models.DateField()
    # organization = ShareForeignKey(Organization, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.organization.name


class Contributor(ShareModel):
    family_name = models.CharField(max_length=200)  # last
    given_name = models.CharField(max_length=200)  # first
    additional_name = models.CharField(max_length=200)  # can be used for middle
    suffix = models.CharField(max_length=50)
    # emails = ShareManyToManyField(Email)
    # emails = models.ManyToManyField(Email, through='ContributorEmail')
    emails = ShareManyToMany(Email, 'ContributorEmail')

    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle


class ContributorEmail(ShareModel):
    # emails_id = models.ForeignKey(Email)
    # contributor_id = models.ForeignKey(Contributor)
    emails_id = ShareForeignKey(Email)
    contributor_id = ShareForeignKey(Contributor)

# class Manuscript(models.Model):
#     title = models.CharField(max_length=200)
#     doi = models.URLField()
