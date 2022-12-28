from typing import Optional
import datetime

from django.db import models
from django.db.models.functions import Coalesce

from share import exceptions
from share.util import BaseJSONAPIMeta, rdfutil


__all__ = ('SourceUniqueIdentifier', )


class SourceUniqueIdentifier(models.Model):
    identifier = models.TextField()
    source_config = models.ForeignKey('SourceConfig', on_delete=models.CASCADE)
    focal_pid_set = models.ManyToManyField('KnownPid')

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        unique_together = ('identifier', 'source_config')
        # indexes = [
        #     models.Index(fields=['referent_pid']),
        # ]

    @property
    def ingest_job(self):
        """fetch the most recent IngestJob for this suid

        (hopefully) temporary -- will be replaced by the inverse relation of a OneToOneField on IngestJob
        """
        return self.ingest_jobs.order_by(
            Coalesce('date_started', 'date_created').desc(nulls_last=True)
        ).first()

    def most_recent_raw_datum(self):
        """fetch the most recent RawDatum for this suid
        """
        return self.raw_data.order_by(
            Coalesce('datestamp', 'date_created').desc(nulls_last=True)
        ).first()

    def get_date_first_seen(self) -> Optional[datetime.datetime]:
        """when the first RawDatum for this suid was added
        """
        return (
            self.raw_data
            .order_by('date_created')
            .values_list('date_created', flat=True)
            .first()
        )

    def as_puri(self):
        """if this suid is known to correspond to a persistent uri, return that uri (else None)
        """
        source = self.source_config.source
        suid_is_osfio_guid = (
            source.canonical
            and source.user.is_trusted
            and source.home_page.startswith(rdfutil.OSFIO)
        )
        if suid_is_osfio_guid:
            return rdfutil.OSFIO[self.identifier]
        return None

    def __repr__(self):
        return '<{}({}, {}, {!r})>'.format('Suid', self.id, self.source_config.label, self.identifier)

    __str__ = __repr__
