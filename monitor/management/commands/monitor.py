import logging

from django.core.management.base import BaseCommand

from share.models import (
    CeleryTaskSentEvent, CeleryTaskReceivedEvent, CeleryTaskStartedEvent, CeleryTaskSucceededEvent,
    CeleryTaskFailedEvent, CeleryTaskRevokedEvent, CeleryTaskRetriedEvent,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        from project.celery import app
        Monitor(app).listen()


class Monitor:
    # http://docs.celeryproject.org/en/latest/userguide/monitoring.html#task-events
    # celery provides basic information fields for all events
    EVENT_BASE_FIELDS = ['uuid', 'hostname', 'pid', 'timestamp']
    TASK_SENT_FIELDS = ['retries', 'eta', 'expires', 'queue', 'exchange', 'routing_key'] + \
                       EVENT_BASE_FIELDS
    TASK_RECEIVED_FIELDS = ['retries', 'eta'] + EVENT_BASE_FIELDS
    TASK_STARTED_FIELDS = EVENT_BASE_FIELDS
    TASK_SUCCEEDED_FIELDS = ['result', 'runtime'] + EVENT_BASE_FIELDS
    TASK_FAILED_FIELDS = ['exception'] + EVENT_BASE_FIELDS
    TASK_REVOKED_FIELDS = ['terminated', 'signum', 'expired'] + EVENT_BASE_FIELDS
    TASK_RETRIED_FIELDS = ['exception'] + EVENT_BASE_FIELDS

    def __init__(self, app):
        self.app = app

    def listen(self):
        with self.app.connection() as connection:
            recv = self.app.events.Receiver(connection, handlers={
                name.replace('_', '-'): getattr(self, name)
                for name in dir(self)
                if name.startswith('task_')
            })
            recv.capture(limit=None, timeout=None, wakeup=True)

    def task_sent(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskSentEvent(**{key: event[key] for key in self.TASK_SENT_FIELDS}).save()

    def task_received(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskReceivedEvent(**{key: event[key] for key in self.TASK_RECEIVED_FIELDS}).save()

    def task_started(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskStartedEvent(**{key: event[key] for key in self.TASK_STARTED_FIELDS}).save()

    def task_succeeded(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskSucceededEvent(**{key: event[key] for key in self.TASK_SUCCEEDED_FIELDS}).save()

    def task_failed(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskFailedEvent(**{key: event[key] for key in self.TASK_FAILED_FIELDS}).save()

    def task_revoked(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskRevokedEvent(**{key: event[key] for key in self.TASK_REVOKED_FIELDS}).save()

    def task_retried(self, event):
        logger.info('%s: %s', event['uuid'], event['type'])
        CeleryTaskRetriedEvent(**{key: event[key] for key in self.TASK_RETRIED_FIELDS}).save()
