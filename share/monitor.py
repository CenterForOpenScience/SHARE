import logging

logger = logging.getLogger(__name__)


class ShareMonitor:

    def __init__(self, app):
        self.app = app
        self.state = app.events.State()

    def listen(self):
        with self.app.connection() as connection:
            recv = self.app.events.Receiver(connection, handlers={
                name.replace('_', '-'): getattr(self, name)
                for name in dir(self)
                if name.startswith('task_')
            })
            recv.capture(limit=None, timeout=None, wakeup=True)

    def task_sent(self, event):
        if not event['name'].startswith('share.tasks'):
            return
        self.state.event(event)
        print(event)

    def task_recieved(self, event):
        self.state.event(event)
        print(event)

    def task_started(self, event):
        self.state.event(event)
        print(event)

    def task_succeeded(self, event):
        self.state.event(event)
        print(event)

    def task_failed(self, event):
        self.state.event(event)
        print(event)

    def task_revoked(self, event):
        self.state.event(event)
        print(event)

    def task_retried(self, event):
        self.state.event(event)
        print(event)
