from datetime import datetime
from pytz import utc

from django.db import models
from typedmodels.models import TypedModel


class CeleryTask(TypedModel):
    uuid = models.UUIDField(db_index=True, unique=True)
    name = models.TextField(blank=True)
    args = models.TextField(blank=True)
    kwargs = models.TextField(blank=True)
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = ['type', 'name', 'app_label', 'date_modified']


class CeleryProviderTask(CeleryTask):
    app_label = models.TextField(db_index=True, blank=True)
    app_version = models.TextField(blank=True)


class CeleryEvent(TypedModel):
    uuid = models.UUIDField(db_index=True)
    hostname = models.TextField()
    pid = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        index_together = ['uuid', 'timestamp']

    # sent/received
    eta = models.DateTimeField(null=True)
    retries = models.IntegerField(null=True)
    # failed/retried
    exception = models.TextField(blank=True)

    def __init__(self, *args, **kwargs):
        if type(kwargs['timestamp']) is float:
            kwargs['timestamp'] = datetime.fromtimestamp(kwargs['timestamp'], tz=utc)
        super().__init__(*args, **kwargs)


class CeleryTaskSentEvent(CeleryEvent):
    expires = models.DateTimeField(null=True)
    queue = models.TextField(blank=True)
    exchange = models.TextField(blank=True)
    routing_key = models.TextField(blank=True)


class CeleryTaskReceivedEvent(CeleryEvent):
    pass


class CeleryTaskStartedEvent(CeleryEvent):
    pass


class CeleryTaskSucceededEvent(CeleryEvent):
    result = models.TextField(blank=True)
    runtime = models.FloatField()


class CeleryTaskFailedEvent(CeleryEvent):
    pass


class CeleryTaskRevokedEvent(CeleryEvent):
    terminated = models.NullBooleanField(null=True)
    signum = models.IntegerField(null=True)
    expired = models.NullBooleanField(null=True)


class CeleryTaskRetriedEvent(CeleryEvent):
    pass
