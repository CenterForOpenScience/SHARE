import contextlib
import traceback
import typing

import celery
from django.conf import settings
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
    WAITING = 'waiting'         # "task__schedule_index_backfill" enqueued
    SCHEDULING = 'scheduling'   # "task__schedule_index_backfill" running (indexer daemon going)
    INDEXING = 'indexing'       # "task__schedule_index_backfill" finished (indexer daemon continuing)
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

    @property
    def strategy_checksum(self):
        # back-compat alias for specific_indexname (may be removed if that's renamed via migration)
        return self.specific_indexname  # for backcompat

    @strategy_checksum.setter
    def strategy_checksum(self, value):
        # back-compat alias for specific_indexname (may be removed if that's renamed via migration)
        self.specific_indexname = value

    @contextlib.contextmanager
    def mutex(self):
        with IndexBackfill.objects.get_with_mutex(pk=self.pk) as index_backfill:
            yield index_backfill
        self.refresh_from_db()

    def pls_start(self, index_strategy):
        with self.mutex() as locked_self:
            assert locked_self.index_strategy_name == index_strategy.strategy_name
            _current_checksum = str(index_strategy.CURRENT_STRATEGY_CHECKSUM)
            if locked_self.strategy_checksum == _current_checksum:
                # what is "current" has not changed -- should be INITIAL
                assert locked_self.backfill_status == IndexBackfill.INITIAL
            else:
                # what is "current" has changed! disregard backfill_status
                locked_self.strategy_checksum = _current_checksum
                locked_self.backfill_status = IndexBackfill.INITIAL
            locked_self.__update_error(None)
            try:
                task__schedule_index_backfill.apply_async((locked_self.pk,))
            except Exception as error:
                locked_self.__update_error(error)
            else:
                locked_self.backfill_status = IndexBackfill.WAITING
            finally:
                locked_self.save()

    def pls_note_scheduling_has_begun(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.WAITING
            locked_self.backfill_status = IndexBackfill.SCHEDULING
            locked_self.save()

    def pls_note_scheduling_has_finished(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.SCHEDULING
            locked_self.backfill_status = IndexBackfill.INDEXING
            locked_self.save()

    def pls_mark_complete(self):
        with self.mutex() as locked_self:
            assert locked_self.backfill_status == IndexBackfill.INDEXING
            locked_self.backfill_status = IndexBackfill.COMPLETE
            locked_self.save()

    def pls_mark_error(self, error: typing.Optional[Exception]):
        with self.mutex() as locked_self:
            locked_self.__update_error(error)
            locked_self.save()

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


@celery.shared_task(bind=True)
def task__schedule_index_backfill(self, index_backfill_pk):
    from share import models as db
    from share.search.index_messenger import IndexMessenger
    from share.search import index_strategy
    from share.search.messages import MessageType
    from trove import models as trove_db

    _index_backfill = db.IndexBackfill.objects.get(pk=index_backfill_pk)
    _index_backfill.pls_note_scheduling_has_begun()
    try:
        _index_strategy = index_strategy.get_strategy(_index_backfill.index_strategy_name)
        _messenger = IndexMessenger(celery_app=self.app, index_strategys=[_index_strategy])
        _messagetype = _index_strategy.backfill_message_type
        assert _messagetype in _index_strategy.supported_message_types
        _target_queryset: models.QuerySet
        if _messagetype == MessageType.BACKFILL_INDEXCARD:
            _target_queryset = (
                trove_db.Indexcard.objects
                .exclude(source_record_suid__source_config__disabled=True)
                .exclude(source_record_suid__source_config__source__is_deleted=True)
            )
        elif _messagetype == MessageType.BACKFILL_SUID:
            _target_queryset = (
                db.SourceUniqueIdentifier.objects
                .exclude(source_config__disabled=True)
                .exclude(source_config__source__is_deleted=True)
            )
        else:
            raise ValueError(f'unknown backfill messagetype {_messagetype}')
        _chunk_size = settings.ELASTICSEARCH['CHUNK_SIZE']
        _messenger.stream_message_chunks(
            _messagetype,
            _target_queryset,
            chunk_size=_chunk_size,
            urgent=False,
        )
    except Exception as error:
        _index_backfill.pls_mark_error(error)
        raise error
    else:
        _index_backfill.pls_note_scheduling_has_finished()
