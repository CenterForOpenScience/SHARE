__all__ = ('FormattedIndexcard',)

from django.db import models
from model_utils import Choices

from share.models.core import NormalizedData
from share.util import BaseJSONAPIMeta
from share.util.extensions import Extensions


class FormattedIndexcardManager(models.Manager):
    def get_or_create_formatted_record(self, suid_id, record_format):
        try:
            return self.get(suid=suid_id, record_format=record_format)
        except self.model.DoesNotExist:
            (_record,) = self.save_formatted_records(
                suid_id=suid_id,
                record_formats=[record_format],
            )
            return _record

    def delete_formatted_records(self, suid):
        self.filter(suid=suid).delete()

    def save_formatted_records(self, suid=None, record_formats=None, normalized_datum=None, suid_id=None):
        if suid is None:
            assert suid_id is not None, 'expected one of suid xor suid_id'
            _suid_id = suid_id
        else:
            assert suid_id is None, 'expected suid xor suid_id, not both'
            _suid_id = suid.id
        if normalized_datum is None:
            normalized_datum = NormalizedData.objects.filter(raw__suid_id=_suid_id).order_by('-created_at').first()
            raw = suid.most_recent_raw_datum()
            normalized_datum = raw.normalizeddata_set.all()
        if record_formats is None:
            record_formats = Extensions.get_names('share.metadata_formats')

        records = []
        for record_format in record_formats:
            formatter = Extensions.get('share.metadata_formats', record_format)()
            formatted_record = formatter.format(normalized_datum)
            record = self._save_formatted_record(_suid_id, record_format, formatted_record)
            if record is not None:
                records.append(record)
        return records

    def _save_formatted_record(self, suid_id, record_format, formatted_record):
        if formatted_record:
            record, _ = self.update_or_create(
                suid_id=suid_id,
                record_format=record_format,
                defaults={
                    'formatted_metadata': formatted_record,
                },
            )
        else:
            self.filter(suid_id=suid_id, record_format=record_format).delete()
            record = None
        return record


class FormattedIndexcard(models.Model):
    CARD_FORMAT = Choices(*Extensions.get_names('share.metadata_formats'))

    objects = FormattedIndexcardManager()

    id = models.AutoField(primary_key=True)
    suid = models.ForeignKey('SourceUniqueIdentifier', on_delete=models.CASCADE)
    record_format = models.TextField(choices=CARD_FORMAT)
    date_modified = models.DateTimeField(auto_now=True)
    formatted_metadata = models.TextField()  # could be JSON, XML, or whatever

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        unique_together = ('suid', 'record_format')
        indexes = [
            models.Index(fields=['date_modified'], name='fmr_date_modified_index')
        ]

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.id}, {self.record_format}, suid:{self.suid_id})>'

    def __str__(self):
        return repr(self)
