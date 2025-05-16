import datetime
from typing import Optional

from django.db import models

from share.util import BaseJSONAPIMeta


class SourceUniqueIdentifier(models.Model):
    '''identifies a metadata record from some external system

    (often abbreviated "suid")
    '''
    identifier = models.TextField()  # no restrictions on identifier format
    source_config = models.ForeignKey('SourceConfig', on_delete=models.CASCADE)
    focus_identifier = models.ForeignKey('trove.ResourceIdentifier', null=True, on_delete=models.PROTECT, related_name='suid_set')
    is_supplementary = models.BooleanField(null=True)

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        unique_together = ('identifier', 'source_config')

    def get_date_first_seen(self) -> Optional[datetime.datetime]:
        """when the first datum for this suid was added
        """
        from trove.models import ArchivedResourceDescription
        return (
            ArchivedResourceDescription.objects
            .filter(indexcard__source_record_suid=self)
            .order_by('created')
            .values_list('created', flat=True)
            .first()
        )

    def get_backcompat_sharev2_suid(self):
        '''get an equivalent "v2_push" suid for this suid

        for filling the legacy suid-based sharev2 index with consistent doc ids

        (may raise SourceUniqueIdentifier.DoesNotExist)
        '''
        from share.models import SourceConfig
        return (
            SourceUniqueIdentifier.objects
            .filter(identifier=self.identifier)
            .filter(source_config__in=SourceConfig.objects.filter(
                source_id=self.source_config.source_id,
                transformer_key='v2_push',
            ))
            .get()
        )

    def has_forecompat_replacement(self) -> bool:
        if self.source_config.transformer_key != 'v2_push':
            return False
        from share.models import SourceConfig
        return (
            SourceUniqueIdentifier.objects
            .filter(identifier=self.identifier)
            .filter(source_config__in=SourceConfig.objects.filter(
                source_id=self.source_config.source_id,
                transformer_key__isnull=True,
            ))
            .exists()
        )

    def __repr__(self):
        return '<{}({}, {}, {!r})>'.format('Suid', self.id, self.source_config.label, self.identifier)

    def __str__(self):
        return self.__repr__()
