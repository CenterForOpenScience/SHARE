from django.db import models
from django.contrib.postgres.fields import JSONField


class Raw(models.Model):
    harvester = models.CharField(max_length=200)
    harvester_version = models.CharField(max_length=200)
    date_harvested = models.DateTimeField('date harvested')
    data = JSONField()
