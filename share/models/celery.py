from celery import states

from django.db import models

from share.models.fields import DateTimeAwareJSONField
from share.models.jobs import get_share_version


ALL_STATES = sorted(states.ALL_STATES)
TASK_STATE_CHOICES = sorted(zip(ALL_STATES, ALL_STATES))


class CeleryTaskResult(models.Model):
    # Explicitly define auto-added field so it can be used in a model index
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')

    correlation_id = models.TextField(blank=True)
    status = models.CharField(db_index=True, max_length=50, default=states.PENDING, choices=TASK_STATE_CHOICES)
    task_id = models.UUIDField(db_index=True, unique=True)

    meta = DateTimeAwareJSONField(null=True, editable=False)
    result = DateTimeAwareJSONField(null=True, editable=False)
    task_name = models.TextField(null=True, blank=True, editable=False, db_index=True)
    traceback = models.TextField(null=True, blank=True, editable=False)

    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    share_version = models.TextField(default=get_share_version, editable=False)

    class Meta:
        verbose_name = 'Celery Task Result'
        verbose_name_plural = 'Celery Task Results'
        indexes = (
            models.Index(fields=['-date_modified', '-id']),
        )

    def as_dict(self):
        return {
            'task_id': self.task_id,
            'status': self.status,
            'result': self.result,
            'date_done': self.date_modified,
            'traceback': self.traceback,
            'meta': self.meta,
        }
