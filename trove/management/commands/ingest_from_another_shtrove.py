import functools
from itertools import islice
import re
from urllib.parse import urlunsplit

from django.conf import settings
from django.core.management.base import BaseCommand
import requests

from share import models as share_db
from trove import digestive_tract
from trove.vocab import mediatypes


class Command(BaseCommand):
    help = "ingest metadata from another SHARE/trove instance"

    def add_arguments(self, parser):
        parser.add_argument("host", help="host name of the shtrove instance (e.g. 'staging-share.osf.io')")
        parser.add_argument("--count", type=int, default=333)

    def handle(self, *args, host, count, **options):
        if not settings.DEBUG:
            raise Exception('this command not meant for non-debug use')
        _ingested_count = 0
        _skipped_count = 0
        for _datum in islice(self._iter_datums(host), count):
            if self._ingest(_datum):
                _ingested_count += 1
            else:
                _skipped_count += 1
        self.stdout.write(
            self.style.SUCCESS(f'ingested {_ingested_count} (skipped {_skipped_count}) from {host}')
        )

    def _iter_datums(self, host: str):
        _url = urlunsplit(('https', host, '/api/v2/rawdata/', '', ''))
        while _url:
            self.stdout.write('fetching a page...')
            _json = requests.get(_url, headers={'Accept': mediatypes.JSONAPI}).json()
            for _item in _json['data']:
                yield _item['attributes']['datum']
            _url = _json['links'].get('next')

    def _ingest(self, datum: str) -> bool:
        # HACK: get only turtle files by checking it starts with a prefix (unreliable, generally, but good enough for this)
        _smells_like_turtle = datum.startswith('@prefix ') or datum.startswith('PREFIX ')
        if _smells_like_turtle:
            _first_subject_match = re.search(
                r'^<([^>\s]+)>',  # HACK: depends on specific serialization
                datum,
                re.MULTILINE,
            )
            if _first_subject_match:
                _subject_iri = _first_subject_match.group(1)
                digestive_tract.swallow(
                    from_user=self._application_user,
                    record=datum,
                    record_identifier=_subject_iri,
                    record_mediatype=mediatypes.TURTLE,
                    focus_iri=_subject_iri,
                )
                return True
        return False

    @functools.cached_property
    def _application_user(self):
        return share_db.ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
