from contextlib import contextmanager

from django.core.management.base import BaseCommand
from django.db import transaction


class Rollback(Exception):
    pass


class BaseShareCommand(BaseCommand):

    @contextmanager
    def rollback_unless_commit(self, commit):
        try:
            with transaction.atomic():

                yield

                if not commit:
                    self.stdout.write('\nRolling back changes...', style_func=self.style.NOTICE)
                    raise Rollback
        except Rollback:
            pass

    def input_confirm(self, prompt, default=None):
        result = input(prompt)
        if not result and default is not None:
            return default
        while len(result) < 1 or result[0].lower() not in 'yn':
            result = input('Please answer yes or no: ')
        return result[0].lower() == 'y'
