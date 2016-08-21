from django.conf import settings


def match_by_module(task_path):
    task_parts = task_path.split('.')
    for i in range(2, len(task_parts) + 1):
        task_subpath = '.'.join(task_parts[:i])
        if task_subpath in settings.LOW_PRI_MODULES:
            return settings.LOW_QUEUE
        if task_subpath in settings.MED_PRI_MODULES:
            return settings.MED_QUEUE
        if task_subpath in settings.HIGH_PRI_MODULES:
            return settings.HIGH_QUEUE
    return settings.DEFAULT_QUEUE


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
