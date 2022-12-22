from django.db import models
from model_utils import Choices

from share.models.suid import SourceUniqueIdentifier
from share.util import BaseJSONAPIMeta
from share.util.extensions import Extensions


class FormattedMetadataRecordManager(models.Manager):
    def delete_formatted_records(self, suid):
        self.filter(suid=suid).delete()

    def save_formatted_records(self, suid, record_formats=None, normalized_datum=None):
        if normalized_datum is None:
            from . import NormalizedData
            normalized_datum = NormalizedData.objects.filter(raw__suid=suid).order_by('-created_at').first()
        if record_formats is None:
            record_formats = Extensions.get_names('share.metadata_formats')

        records = []
        for record_format in record_formats:
            formatted_record = self.get_formatter(record_format).format(normalized_datum)
            record = self._save_formatted_record(suid, record_format, formatted_record)
            if record is not None:
                records.append(record)
        return records

    def get_formatted(self, suid, record_format):
        try:
            return self.get(suid=suid, record_format=record_format)
        except self.model.DoesNotExist:
            records = self.save_formatted_records(suid, record_formats=[record_format])
            return records[0] if records else None

    def get_by_pid(self, pid_uri, record_format):
        suid_qs = (
            SourceUniqueIdentifier.objects
            .filter(focal_pid_set__uri=pid_uri)
            .annotate(
                _formatted_record=(
                    self.filter(suid_id=models.OuterRef('id'), record_format=record_format)
                    .values('formatted_metadata')
                    [:1]
                ),
            )
        )

        for suid in suid_qs:
            if suid._formatted_record:
                yield suid._formatted_record
            else:
                records = self.save_formatted_records(suid, record_formats=[record_format])
                if records:
                    yield records[0]

    def get_formatter(self, record_format):
        formatter_class = Extensions.get('share.metadata_formats', record_format)
        return formatter_class()

    def _save_formatted_record(self, suid, record_format, formatted_record):
        record = None
        if formatted_record is None:
            self.filter(suid=suid, record_format=record_format).delete()
        else:
            record, _ = self.update_or_create(
                suid=suid,
                record_format=record_format,
                defaults={
                    'formatted_metadata': formatted_record,
                },
            )
        return record


class FormattedMetadataRecord(models.Model):
    RECORD_FORMAT = Choices(*Extensions.get_names('share.metadata_formats'))

    objects = FormattedMetadataRecordManager()

    id = models.AutoField(primary_key=True)
    suid = models.ForeignKey('SourceUniqueIdentifier', on_delete=models.CASCADE)
    record_format = models.TextField(choices=RECORD_FORMAT)
    date_modified = models.DateTimeField(auto_now=True)
    formatted_metadata = models.TextField()  # could be JSON, XML, or whatever

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        unique_together = ('suid', 'record_format')
        indexes = [
            models.Index(fields=['date_modified'], name='fmr_date_modified_index'),
        ]

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.id}, {self.record_format}, suid:{self.suid_id})>'

    def __str__(self):
        return repr(self)
