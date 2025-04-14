from collections import Counter

from django.db.models import OuterRef, Exists
from django.utils.translation import gettext as _

from share.management.commands import BaseShareCommand
from share import models as _db


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('--really-really', action='store_true', help='')

    def handle(self, *args, really_really: bool, **kwargs):
        # delete all SourceConfigs except those for trove ingest
        _sourceconfigs_to_delete = _db.SourceConfig.objects.exclude(transformer_key='rdf')
        if not _sourceconfigs_to_delete.exists():
            self.stdout.write(self.style.SUCCESS(_('nothing to delete')))
            return
        _prior_counts = {
            _db.SourceConfig: _sourceconfigs_to_delete.count(),
            _db.RawDatum: (
                _db.RawDatum.objects
                .filter(suid__source_config__in=_sourceconfigs_to_delete)
                .fuzzy_count()
            ),
        }
        for _modelcls, _count in _prior_counts.items():
            self.stdout.write(f'{_modelcls.__name__}: {_count}')
        # confirm and delete
        if really_really or self.input_confirm(self.style.WARNING(_('really DELETE ALL pre-trove data and sources? (y/n)'))):
            self.stdout.write(_('deleting...'))
            _deleted_total, _deleted_counts = _sourceconfigs_to_delete.delete()
            for _name, _count in _deleted_counts.items():
                self.stdout.write(self.style.SUCCESS(f'{_name}: deleted {_count}'))
        else:
            self.stdout.write(self.style.SUCCESS('deleted nothing'))
