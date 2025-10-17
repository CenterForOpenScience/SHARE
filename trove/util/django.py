from __future__ import annotations
from collections.abc import Generator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


__all__ = ('pk_chunked',)


def pk_chunked(queryset: QuerySet, chunksize: int) -> Generator[list]:
    '''pk_chunked: get primary key values, in chunks, for the given queryset

    yields non-empty lists of primary keys up to `chunksize` long
    '''
    _ordered_qs = queryset.order_by('pk')
    _prior_end_pk = None
    _chunk_qs: QuerySet | None = _ordered_qs
    while _chunk_qs is not None:  # for each chunk:
        # load primary key values only
        _pks = list(_chunk_qs.values_list('pk', flat=True)[:chunksize])
        if _pks:
            _end_pk = _pks[-1]
            if (_prior_end_pk is not None) and (_end_pk <= _prior_end_pk):
                raise RuntimeError(f'sentinel pks not ascending?? got {_end_pk} after {_prior_end_pk}')
            yield _pks
            _prior_end_pk = _end_pk
            _chunk_qs = _ordered_qs.filter(pk__gt=_prior_end_pk)
        else:
            _chunk_qs = None  # done
