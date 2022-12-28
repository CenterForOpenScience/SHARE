import rdflib

from django.db import models

from share import exceptions
from share.models.fields import ShareURLField
from share.util import rdfutil


class KnownPidManager(models.Manager):
    def set_focal_pids(self, suid, rdfgraph):
        pids = set()
        try:
            pid_from_suid = rdfutil.normalize_pid_uri(suid.identifier)
        except exceptions.BadPid:
            pass
        else:
            pids.add(pid_from_suid)
        if pid_from_suid and rdfgraph:
            pid_synonyms = rdfgraph.objects(
                subject=rdflib.URIRef(pid_from_suid),
                predicate=rdflib.OWL.sameAs,
            )
            for pid_synonym in pid_synonyms:
                try:
                    pids.add(rdfutil.normalize_pid_uri(pid_synonym))
                except exceptions.BadPid:
                    pass

        known_pids = [
            KnownPid.objects.get_or_create(uri=pid_uri)
            for pid_uri in pids
        ]
        suid.focal_pid_set.set(known_pids)


class KnownPid(models.Model):
    uri = ShareURLField(unique=True)

    def save(self, *args, **kwargs):
        # TODO: require known pid domain?
        self.uri = rdfutil.normalize_pid_uri(self.uri)
        return super().save(*args, **kwargs)
