from django.conf import settings

from share.models import ShareUser
from share.management.commands import BaseShareCommand
from trove import digestive_tract
from trove.vocab import VOCAB_SET


def ingest_vocabs(system_user: ShareUser):
    for _vocab in VOCAB_SET:
        digestive_tract.swallow(
            from_user=system_user,
            record=_vocab.turtle(),
            record_identifier=_vocab.turtle_filename,
            record_mediatype='text/turtle',
            resource_iri=_vocab.turtle_focus_iri,
        )


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _system_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        ingest_vocabs(_system_user)
