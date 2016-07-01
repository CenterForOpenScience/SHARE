from datetime import datetime
from pytz import utc

from django.db import models
from typedmodels.models import TypedModel

from share.models.core import ShareUser


class CeleryTask(TypedModel):
    uuid = models.UUIDField(db_index=True, unique=True)
    name = models.TextField(blank=True)
    args = models.TextField(blank=True)
    kwargs = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def status(self):
        return CeleryEvent.objects.filter(uuid=self.uuid).order_by('-timestamp').first().type

    class Meta:
        index_together = ['type', 'name', 'app_label', 'timestamp']


class CeleryProviderTask(CeleryTask):
    app_label = models.TextField(db_index=True, blank=True)
    app_version = models.TextField(blank=True)
    provider = models.ForeignKey(ShareUser, related_name='provider')
    started_by = models.ForeignKey(ShareUser, related_name='started_by')


class CeleryEvent(TypedModel):
    uuid = models.UUIDField(db_index=True)
    hostname = models.TextField()
    pid = models.IntegerField()
    timestamp = models.DateTimeField()

    # sent/received
    eta = models.DateTimeField(null=True)
    retries = models.IntegerField(null=True)
    # failed/retried
    exception = models.TextField(blank=True)

    class Meta:
        index_together = ['uuid', 'timestamp']

    def __init__(self, *args, **kwargs):
        if type(kwargs.get('timestamp')) is float:
            kwargs['timestamp'] = datetime.fromtimestamp(kwargs['timestamp'], tz=utc)
        super().__init__(*args, **kwargs)


class CeleryTaskSentEvent(CeleryEvent):
    expires = models.DateTimeField(null=True)
    queue = models.TextField(blank=True)
    exchange = models.TextField(blank=True)
    routing_key = models.TextField(blank=True)

    class Meta:
        verbose_name = 'task-sent'


class CeleryTaskReceivedEvent(CeleryEvent):
    class Meta:
        verbose_name = 'task-received'



class CeleryTaskStartedEvent(CeleryEvent):
    class Meta:
        verbose_name = 'task-started'


class CeleryTaskSucceededEvent(CeleryEvent):
    result = models.TextField(blank=True)
    runtime = models.FloatField()

    class Meta:
        verbose_name = 'task-succeeded'


class CeleryTaskFailedEvent(CeleryEvent):
    class Meta:
        verbose_name = 'task-failed'


class CeleryTaskRevokedEvent(CeleryEvent):
    terminated = models.NullBooleanField(null=True)
    signum = models.IntegerField(null=True)
    expired = models.NullBooleanField(null=True)

    class Meta:
        verbose_name = 'task-revoked'


class CeleryTaskRetriedEvent(CeleryEvent):
    class Meta:
        verbose_name = 'task-retried'
