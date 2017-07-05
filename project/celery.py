import os

import celery

from raven.contrib.celery import register_signal, register_logger_signal

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from django.conf import settings  # noqa

from share.sentry import sentry_client  # noqa


class Celery(celery.Celery):

    def on_configure(self):
        if not sentry_client.is_enabled():
            return

        register_signal(sentry_client)
        register_logger_signal(sentry_client)

app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks([
    'share',
    'share.janitor',
    'bots.elasticsearch',
])
