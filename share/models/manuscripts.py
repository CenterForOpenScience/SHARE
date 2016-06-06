from django.db import models
from django.contrib.postgres.fields import JSONField
from share.models.contributor import Contributor


class Manuscript(models.Model):
    title = models.CharField(max_length=200)
    doi = models.URLField(null=True)
    contributors = models.ManyToManyField(Contributor)

    def __str__(self):
        return "{}".format(self.title)