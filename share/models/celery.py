from celery import states

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from model_utils import Choices

from typedmodels.models import TypedModel

from share.models.fields import DateTimeAwareJSONField
from share.models.fuzzycount import FuzzyCountManager
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


class UnusedCeleryTask(TypedModel):
    """Keeping this model around so we have the data to refer back to, if need be.
    """
    STATUS = Choices(
        (0, 'started', _('started')),
        (1, 'retried', _('retried')),
        (2, 'failed', _('failed')),
        (3, 'succeeded', _('succeeded')),
    )

    uuid = models.UUIDField(db_index=True, unique=True)
    name = models.TextField(blank=True, db_index=True)
    args = models.TextField(blank=True)
    kwargs = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='started_by', null=True, on_delete=models.CASCADE)
    # TODO rename to 'source'
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='provider', null=True, on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS)

    objects = FuzzyCountManager()

    class Meta:
        ordering = ('-timestamp',)
        index_together = ('type', 'name', 'app_label', 'timestamp')


class UnusedCeleryProviderTask(UnusedCeleryTask):
    app_label = models.TextField(db_index=True, blank=True)
    app_version = models.TextField(db_index=True, blank=True)
