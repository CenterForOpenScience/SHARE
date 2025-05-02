from django.db.models import OuterRef, Exists
from django.utils.translation import gettext as _

from share.management.commands import BaseShareCommand
from share import models as _db


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--really-really', action='store_true', help='skip final confirmation prompt before really deleting')

    def handle(self, *args, really_really: bool, **kwargs):
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
        self.stdout.write(self.style.WARNING(_('pre-trove source-configs with deletable rawdata:')))
        for _label in _pretrove_configs_with_rawdata.values_list('label', flat=True):
            self.stdout.write(f'\t{_label}')
        if really_really or self.input_confirm(self.style.WARNING(_('really DELETE ALL raw metadata records belonging to these source-configs? (y/n)'))):
            self.stdout.write(_('deleting...'))
            _rawdata_to_delete = (
                _db.RawDatum.objects
                .filter(suid__source_config_id__in=_pretrove_configs)
            )
            _deleted_total, _deleted_counts = _rawdata_to_delete.delete()
            for _name, _count in _deleted_counts.items():
                self.stdout.write(self.style.SUCCESS(f'{_name}: deleted {_count}'))
        else:
            self.stdout.write(self.style.SUCCESS('deleted nothing'))
