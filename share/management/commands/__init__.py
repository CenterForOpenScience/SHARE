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
