from django.db.models import OuterRef, Exists
from django.utils.translation import gettext as _

from share.management.commands import BaseShareCommand
from share import models as _db


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--chunksize', type=int, default=1024, help='number of RawData per DELETE')
        parser.add_argument('--really-really', action='store_true', help='skip final confirmation prompt before really deleting')

    def handle(self, *args, chunksize: int, really_really: bool, **kwargs):
        # note: `share.transform` deleted; `transformer_key` always null for trove-ingested rdf
        _pretrove_configs = _db.SourceConfig.objects.filter(transformer_key__isnull=False)
        _pretrove_configs_with_rawdata = (
            _pretrove_configs
            .annotate(has_rawdata=Exists(
                _db.RawDatum.objects
                .filter(suid__source_config_id=OuterRef('pk'))
            ))
            .filter(has_rawdata=True)
        )
        if not _pretrove_configs_with_rawdata.exists():
            self.stdout.write(self.style.SUCCESS(_('nothing to delete')))
            return
        _sourceconfig_ids_and_labels = list(
            _pretrove_configs_with_rawdata.values_list('id', 'label'),
        )
        self.stdout.write(self.style.WARNING(_('pre-trove source-configs with deletable rawdata:')))
        for __, _sourceconfig_label in _sourceconfig_ids_and_labels:
            self.stdout.write(f'\t{_sourceconfig_label}')
        if really_really or self.input_confirm(self.style.WARNING(_('really DELETE ALL raw metadata records belonging to these source-configs? (y/n)'))):
            _total_deleted = 0
            for _sourceconfig_id, _sourceconfig_label in _sourceconfig_ids_and_labels:
                _total_deleted += self._do_delete_rawdata(_sourceconfig_id, _sourceconfig_label, chunksize)
            self.stdout.write(self.style.SUCCESS(_('deleted %(count)s items') % {'count': _total_deleted}))
        else:
            self.stdout.write(self.style.SUCCESS(_('deleted nothing')))

    def _do_delete_rawdata(self, sourceconfig_id, sourceconfig_label, chunksize) -> int:
        # note: `.delete()` cannot be called on sliced querysets, so chunking is more complicated
        # -- before deleting each chunk, query for its last pk to filter on as a sentinel value
        _prior_sentinel_pk = None
        _deleted_count = 0
        _rawdata_qs = (
            _db.RawDatum.objects
            .filter(suid__source_config_id=sourceconfig_id)
            .order_by('pk')  # for consistent chunking
        )
        self.stdout.write(_('%(label)s: deleting all rawdata...') % {'label': sourceconfig_label})
        while True:  # for each chunk:
            _pk_qs = _rawdata_qs.values_list('pk', flat=True)
            # get the last pk in the chunk
            _sentinel_pk = _pk_qs[chunksize - 1: chunksize].first() or _pk_qs.last()
            if _sentinel_pk is not None:
                if (_prior_sentinel_pk is not None) and (_sentinel_pk <= _prior_sentinel_pk):
                    raise RuntimeError(f'sentinel pks not ascending?? got {_sentinel_pk} after {_prior_sentinel_pk}')
                _prior_sentinel_pk = _sentinel_pk
                _chunk_to_delete = _rawdata_qs.filter(pk__lte=_sentinel_pk)
                _chunk_deleted_count, _by_model = _chunk_to_delete.delete()
                if _by_model and set(_by_model.keys()) != {'share.RawDatum'}:
                    raise RuntimeError(f'deleted models other than RawDatum?? {_by_model}')
                self.stdout.write(
                    _('%(label)s: deleted %(count)s') % {'label': sourceconfig_label, 'count': _chunk_deleted_count},
                )
                _deleted_count += _chunk_deleted_count
                continue  # next chunk
            # end
            self.stdout.write(self.style.SUCCESS(
                _('%(label)s: done; deleted %(count)s') % {'label': sourceconfig_label, 'count': _deleted_count},
            ))
            return _deleted_count
