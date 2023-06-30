import datetime
from typing import Optional

from django.db import models
from django.db.models.functions import Coalesce

from share.util import BaseJSONAPIMeta


class SourceUniqueIdentifier(models.Model):
    '''identifies a metadata record from some external system
    '''
    identifier = models.TextField()  # no restrictions on identifier format
    source_config = models.ForeignKey('SourceConfig', on_delete=models.CASCADE)
    resource_piri = models.ForeignKey('trove.PersistentIri', null=True, on_delete=models.PROTECT, related_name='synonymous_suid_set')

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        unique_together = ('identifier', 'source_config')

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

    def __repr__(self):
        return '<{}({}, {}, {!r})>'.format('Suid', self.id, self.source_config.label, self.identifier)

    def __str__(self):
        return self.__repr__()
