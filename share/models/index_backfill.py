import traceback

from django.db import models


class IndexBackfill(models.Model):
    INITIAL = 'initial'         # default state; nothing else happen
    WAITING = 'waiting'         # "schedule_index_backfill" triggered
    SCHEDULING = 'scheduling'   # "schedule_index_backfill" running (indexer daemon going)
    INDEXING = 'indexing'       # "schedule_index_backfill" finished (indexer daemon continuing)
    COMPLETE = 'complete'       # admin confirmed backfill complete
    ERROR = 'error'             # something wrong (check error_* fields)
    BACKFILL_STATUS_CHOICES = (
        (INITIAL, INITIAL),
        (WAITING, WAITING),
        (SCHEDULING, SCHEDULING),
        (INDEXING, INDEXING),
        (COMPLETE, COMPLETE),
        (ERROR, ERROR),
    )
    backfill_status = models.TextField(choices=BACKFILL_STATUS_CHOICES, default=INITIAL)
    index_strategy_name = models.TextField(unique=True)
    specific_indexname = models.TextField()
    error_type = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    error_context = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return (
            f'{self.__class__.__name__}('
            f'backfill_status="{self.backfill_status}", '
            f'index_strategy_name="{self.index_strategy_name}", '
            f'modified="{self.modified.isoformat(timespec="minutes")}", '
            ')'
        )

    def __str__(self):
        return repr(self)

    def update_error(self, error):
        if isinstance(error, Exception):
            tb = traceback.TracebackException.from_exception(error)
            self.error_type = type(error).__name__
            self.error_message = str(error)
            self.error_context = '\n'.join(tb.format(chain=True))
        elif error is None:
            self.error_type = ''
            self.error_message = ''
            self.error_context = ''
        self.save()
