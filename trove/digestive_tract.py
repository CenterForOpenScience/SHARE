'''a small interface for ingesting metadata records

leaning (perhaps too far) into the "ingest" metaphor

swallow: store a given record by checksum; queue for extraction
extract: gather rdf graph from a record; store as index card(s)
excrete: send extracted index card to every public search index
'''
__all__ = ('swallow', 'extract', 'excrete')

import hashlib
import logging

from django.db import transaction
from django.utils import timezone
import gather

from share.exceptions import IngestError
from share.extract import get_rdf_extractor_class
from share.search.index_messenger import IndexMessenger
from share.search.messages import MessageType
from share import models as share_db
from trove import models as trove_db


logger = logging.getLogger(__name__)


@transaction.atomic
def swallow(
    *,  # all keyword-args
    record: str,
    record_identifier: str,
    record_mediatype: str,
    record_focus_iri: str,
    user: share_db.ShareUser,
    datestamp=None,  # default "now"
) -> share_db.IngestJob:
    '''swallow: store a given record by checksum; queue for extraction

    will create (or update) one of each:
        Source (from whom/where is it?)
        SourceConfig (how did/do we get it?)
        SourceUniqueIdentifier (by what name do/would they know it?)
        RawDatum ("it", a metadata record)
    '''
    if not record_identifier:
        raise IngestError('datum_identifier required (for suid\'s sake)')
    if not isinstance(record, str):
        raise IngestError('datum must be a string')
    _source_config = share_db.SourceConfig.objects.get_or_create_push_config(user)
    _focus_piri = trove_db.PersistentIri.objects.save_for_iri(record_focus_iri)
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.get_or_create(
        source_config=_source_config,
        identifier=record_identifier,
        defaults={
            'record_focus_piri': _focus_piri,
        },
    )
    if (not _suid_created) and (_focus_piri.id != _suid.record_focus_piri_id):
        if _suid.record_focus_piri_id is not None:
            logger.warn(
                'overwriting suid.record_focus_piri from'
                f' "{_suid.record_focus_piri.as_str()}" to "{_focus_piri.as_str()}"'
                ' (maybe fine, but such clobbering should be rare)'
            )
        _suid.record_focus_piri = _focus_piri
        _suid.save()
    _raw, _raw_created = share_db.RawDatum.objects.update_or_create(
        suid=_suid,
        sha256=hashlib.sha256(record.encode()).hexdigest(),
        defaults={
            'datum': record,
            'mediatype': record_mediatype,
            'datestamp': (datestamp or timezone.now()),
        },
    )
    # TODO
    return IngestScheduler().schedule(_raw.suid, _raw.id)


def extract(raw: share_db.RawDatum) -> list[trove_db.RdfIndexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    will create (or update):
        RdfIndexcard (all extracted metadata)
        FormattedIndexcard (formatted version of RdfIndexcard
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    _tripledict: gather.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    _focus_iri = raw.suid.record_focus_piri.find_equivalent_iri(_tripledict)
    # TODO handle _focus_iri not found
    # TODO if not _tripledict: raw.save(update_fields=['no_output'])
    _cards = [
        trove_db.RdfIndexcard.objects.save_indexcard(
            from_raw_datum=raw,
            focus_iri=_focus_iri,
            card_as_tripledict=_tripledict,
        ),
    ]
    # any iri that has the focus iri as prefix is interpreted as a separate vocab term
    for _iri, _twopledict in _tripledict.items():
        if _iri.startswith(_focus_iri) and (_iri != _focus_iri):
            _cards.append(trove_db.RdfIndexcard.objects.save_indexcard(
                from_raw_datum=raw,
                focus_iri=_iri,
                card_as_tripledict={_iri: _twopledict},
            ))
    # TODO: DerivedIndexcards
    return _cards


def excrete(suid, *, urgent: bool, index_messenger=None):
    '''excrete: send extracted index card to every public search index
    '''
    _index_messenger = index_messenger or IndexMessenger()
    _index_messenger.send_message(MessageType.INDEX_SUID, [suid.id], urgent=urgent)
    # TODO: receive message correctly -- load from RdfIndexcard, not FormattedMetadataRecord
