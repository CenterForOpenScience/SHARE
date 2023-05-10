import os

import celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from django.conf import settings  # noqa


app = celery.Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks([
    'share',
    'share.janitor',
])
