import os

import celery

from raven.contrib.celery import register_signal, register_logger_signal

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from django.conf import settings  # noqa


class Celery(celery.Celery):

    def on_configure(self):
        # Import has to be relative. "client" is not actually lazily initialized
        from raven.contrib.django.raven_compat.models import client

        if not client.is_enabled():
            return

        register_signal(client)
        register_logger_signal(client)


app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks([
    'share',
    'share.janitor',
    'bots.elasticsearch',
])
