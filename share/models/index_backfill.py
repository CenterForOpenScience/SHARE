import contextlib
import traceback
import typing

from django.db import models, transaction

from share import exceptions


class IndexBackfillManager(models.Manager):
    @contextlib.contextmanager
    def get_with_mutex(self, **backfill_filter_kwargs):
        # select_for_update provides a mutual-exclusion lock across transactions,
        # so only one block of code wrapped in this context manager can run at once
        # per IndexBackfill instance (to keep lifecycle actions coherent)
        with transaction.atomic():
            index_backfill_list = list(
                self.filter(**backfill_filter_kwargs)
                .select_for_update()
            )
            if not index_backfill_list:
                raise exceptions.ShareException(
                    f'found no {self.model.__name__} matching filter {backfill_filter_kwargs}'
                )
            if len(index_backfill_list) != 1:
                raise exceptions.ShareException(
                    f'may lock only one {self.model.__name__} at a time; don\'t get greedy'
                    f' ({len(index_backfill_list)} results for filter {backfill_filter_kwargs})'
                )
            yield index_backfill_list[0]


class IndexBackfill(models.Model):
    INITIAL = 'initial'         # default state; nothing else happen
    WAITING = 'waiting'         # "schedule_index_backfill" enqueued
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

    objects = IndexBackfillManager()  # custom manager

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

    @contextlib.contextmanager
    def mutex(self):
        with IndexBackfill.objects.get_with_mutex(pk=self.pk) as index_backfill:
            yield index_backfill

    def pls_start(self, index_strategy):
        with self.mutex() as locked_self:
            assert locked_self.index_strategy_name == index_strategy.name
            current_index = index_strategy.for_current_index()
            if locked_self.specific_indexname == current_index.indexname:
                # what is "current" has not changed -- should already be INITIAL
                assert locked_self.backfill_status == IndexBackfill.INITIAL
            else:
                # what is "current" has changed! disregard backfill_status
                locked_self.specific_indexname = current_index.indexname
                locked_self.backfill_status = IndexBackfill.INITIAL
            locked_self.__update_error(None)
            try:
                import share.tasks
                share.tasks.schedule_index_backfill.apply_async((locked_self.pk,))
            except Exception as error:
                locked_self.__update_error(error)
            else:
                locked_self.backfill_status = IndexBackfill.WAITING
            finally:
                locked_self.save()
        self.refresh_from_db()

    def pls_note_scheduling_has_begun(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.WAITING
            locked_self.backfill_status = IndexBackfill.SCHEDULING
            locked_self.save()
        self.refresh_from_db()

    def pls_note_scheduling_has_finished(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.SCHEDULING
            locked_self.backfill_status = IndexBackfill.INDEXING
            locked_self.save()
        self.refresh_from_db()

    def pls_mark_complete(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.INDEXING
            locked_self.backfill_status = IndexBackfill.COMPLETE
            locked_self.save()
        self.refresh_from_db()

    def pls_mark_error(self, error: typing.Optional[Exception]):
        with self.mutex() as locked_self:
            locked_self.__update_error(error)
            locked_self.save()
        self.refresh_from_db()

    def __update_error(self, error):
        if isinstance(error, Exception):
            tb = traceback.TracebackException.from_exception(error)
            self.error_type = type(error).__name__
            self.error_message = str(error)
            self.error_context = '\n'.join(tb.format(chain=True))
            self.backfill_status = self.ERROR
        elif error is None:
            self.error_type = ''
            self.error_message = ''
            self.error_context = ''
        else:
            raise NotImplementedError(f'expected Exception or None (got {error})')
