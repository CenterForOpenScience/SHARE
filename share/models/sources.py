import logging

from django.db import models

from share.models.ingest import SourceConfig

logger = logging.getLogger(__name__)
__all__ = ('SourceStat',)


class SourceStat(models.Model):
    config = models.ForeignKey(SourceConfig, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    response_status_code = models.SmallIntegerField(blank=True, null=True)
    response_elapsed_time = models.FloatField(blank=True, null=True)
    response_exception = models.TextField(blank=True, null=True)
    earliest_datestamp_config = models.DateField(blank=True, null=True)
    base_url_config = models.TextField()
    admin_note = models.TextField(blank=True)
    grade = models.FloatField()

    # OAI specific
    earliest_datestamp_source = models.DateField(blank=True, null=True)
    earliest_datestamps_match = models.BooleanField(default=False)

    base_url_source = models.TextField(blank=True, null=True)
    base_urls_match = models.BooleanField(default=False)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.pk, self.config.label)

    def __str__(self):
        return '{}: {}'.format(self.config.source.long_title, self.config.label)
