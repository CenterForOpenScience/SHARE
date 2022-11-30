from django.db import models

from share.models.fields import ShareURLField
from share.util import rdfutil


class KnownPid(models.Model):
    uri = ShareURLField(unique=True)

    def save(self, *args, **kwargs):
        # TODO: require known pid domain?
        self.uri = rdfutil.normalize_pid_uri(self.uri)
        return super().save(*args, **kwargs)
