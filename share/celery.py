import logging

import raven

from django.conf import settings

from djcelery.backends.database import DatabaseBackend as DjCeleryDatabaseBackend


logger = logging.getLogger(__name__)

if hasattr(settings, 'RAVEN_CONFIG') and settings.RAVEN_CONFIG['dsn']:
    client = raven.Client(settings.RAVEN_CONFIG['dsn'])
else:
    client = None


def match_by_module(task_path):
    task_parts = task_path.split('.')
    for i in range(2, len(task_parts) + 1):
        task_subpath = '.'.join(task_parts[:i])
        for v in settings.QUEUES.values():
            if task_subpath in v['modules']:
                return v['name']
    return settings.QUEUES['DEFAULT']['name']


class CeleryRouter(object):
    def route_for_task(self, task, args=None, kwargs=None):
        """ Handles routing of celery tasks.
        See http://docs.celeryproject.org/en/latest/userguide/routing.html#routers
        :param str task:    Of the form 'full.module.path.to.class.function'
        :returns dict:      Tells celery into which queue to route this task.
        """
        return {
            'queue': match_by_module(task)
        }


class DatabaseBackend(DjCeleryDatabaseBackend):

    def _handle_unhandled_exception(self, exc):
        try:
            logger.exception(exc)
            logger.critical('Caught an unhandled exception in the result backend, killing process')
            if client:
                client.capture_exceptions(sample_rate=0.5)
        except Exception as e:
            logger.exception()
            logger.critical('Failed to log a previous failure')
            if client:
                client.capture_exceptions(sample_rate=0.5)
        finally:
            raise SystemExit(57)  # Something a bit less generic than 1 or -1

    def _store_result(self, task_id, result, status, traceback=None, request=None):
        try:
            return super()._store_result(task_id, result, status, traceback=traceback, request=result)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def _save_group(self, group_id, result):
        try:
            return super()._save_group(group_id, result)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def _get_task_meta_for(self, task_id):
        try:
            return super()._get_task_meta_for(task_id)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def _restore_group(self, group_id):
        try:
            return super()._restore_group(group_id)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def _delete_group(self, group_id):
        try:
            return super()._delete_group(group_id)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def _forget(self, task_id):
        try:
            return super()._forget(task_id)
        except Exception as e:
            self._handle_unhandled_exception(e)

    def cleanup(self):
        try:
            return super().cleanup()
        except Exception as e:
            self._handle_unhandled_exception(e)
