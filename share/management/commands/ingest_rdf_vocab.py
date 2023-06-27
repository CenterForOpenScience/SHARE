from django.conf import settings

from share.models import ShareUser, Source
from share.management.commands import BaseShareCommand
from trove import digestive_tract


vocab_turtles = {
    'http://purl.org/dc/terms/': 'trove/vocab/dublin_core_terms.ttl',
}


def ingest_vocabs():
    _system_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
    for _vocab_iri, _file_path in vocab_turtles.items():
        with open(_file_path) as _vocab_file:
            _vocab_record = _vocab_file.read()
        digestive_tract.swallow(
            from_user=_system_user,
            record=_vocab_record,
            record_identifier=_file_path,
            record_mediatype='text/turtle',
            record_focus_iri_set=[_vocab_iri],
        )


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        ingest_vocabs()
