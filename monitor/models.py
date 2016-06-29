from datetime import datetime
from pytz import utc

from django.db import models
from typedmodels.models import TypedModel


class CeleryEvent(TypedModel):
    uuid = models.UUIDField(db_index=True)
    hostname = models.TextField()
    pid = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        index_together = ['uuid', 'timestamp']

    # sent/received
    name = models.TextField(blank=True)
    args = models.TextField(blank=True)
    kwargs = models.TextField(blank=True)
    eta = models.DateTimeField(null=True)
    retries = models.IntegerField(null=True)
    # failed/retried
    exception = models.TextField(blank=True)

    def __init__(self, *args, **kwargs):
        if type(kwargs['timestamp']) is float:
            kwargs['timestamp'] = datetime.fromtimestamp(kwargs['timestamp'], tz=utc)
        super().__init__(*args, **kwargs)


class TaskSentEvent(CeleryEvent):
    expires = models.DateTimeField(null=True)
    queue = models.TextField(blank=True)
    exchange = models.TextField(blank=True)
    routing_key = models.TextField(blank=True)


class TaskReceivedEvent(CeleryEvent):
    pass


class TaskStartedEvent(CeleryEvent):
    pass


class TaskSucceededEvent(CeleryEvent):
    result = models.TextField(blank=True)
    runtime = models.FloatField()


class TaskFailedEvent(CeleryEvent):
    pass


class TaskRevokedEvent(CeleryEvent):
    terminated = models.NullBooleanField(null=True)
    signum = models.IntegerField(null=True)
    expired = models.NullBooleanField(null=True)


class TaskRetriedEvent(CeleryEvent):
    pass
