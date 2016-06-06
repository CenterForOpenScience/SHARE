from django.db import models
from django.contrib.postgres.fields import JSONField


class Organization(models.Model):
    name = models.CharField(max_length=200)
    #parent = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)


class Email(models.Model):
    is_primary = models.BooleanField()
    email = models.EmailField()

    def __str__(self):
        return self.email


class Affiliation(models.Model):

    start_date = models.DateField()
    end_date = models.DateField()
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.organization.name

class Contributor(models.Model):
    family_name = models.CharField(max_length=200) # last
    given_name = models.CharField(max_length=200) # first
    additional_name = models.CharField(max_length=200, null=True) # can be used for middle
    suffix = models.CharField(max_length=50, null=True)

    affiliations = models.ManyToManyField(Affiliation)
    emails = models.ManyToManyField(Email)
    # current_affiliation =
    # other_properties = models.JSONField()
    # suffix
    # non-dropping-particle
    # dropping-particle

    def __str__(self):
        return "{} {}".format(self.given_name, self.family_name)
#
# class Manuscript(models.Model):
#     title = models.CharField(max_length=200)
#     doi = models.URLField()