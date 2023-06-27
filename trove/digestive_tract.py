'''a small interface for ingesting metadata records

leaning (perhaps too far) into the "ingest" metaphor

swallow: store a given record by checksum; queue for extraction
extract: gather rdf graph from a record; store as index card(s)
excrete: send extracted index card to every public search index
'''
__all__ = ('swallow', 'extract', 'excrete')

import hashlib
import logging
import typing

from django.db import transaction
from django.utils import timezone
import gather
import sentry_sdk

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
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    record_mediatype: str,
    record_focus_iri_set: typing.Iterable[str],
    datestamp=None,  # default "now"
) -> share_db.IngestJob:
    '''swallow: store a given record by checksum; queue for extraction

    will create (or update) one of each:
        Source (from whom/where is it?)
        SourceConfig (how did/do we get it?)
        SourceUniqueIdentifier (by what name do/would they know it?)
        RawDatum ("it", a metadata record)
    '''
    if not isinstance(record, str):
        raise IngestError('datum must be a string')
    _source_config = share_db.SourceConfig.objects.get_or_create_push_config(from_user)
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.get_or_create(
        source_config=_source_config,
        identifier=record_identifier,
    )
    _suid.record_focus_piri_set.set([
        trove_db.PersistentIri.objects.save_for_iri(_focus_iri)
        for _focus_iri in set(record_focus_iri_set)
    ])
    _datestamp = datestamp or timezone.now()
    _raw, _raw_created = share_db.RawDatum.objects.get_or_create(
        suid=_suid,
        sha256=hashlib.sha256(record.encode()).hexdigest(),
        defaults={
            'datum': record,
            'mediatype': record_mediatype,
            'datestamp': _datestamp,
        },
    )
    if not _raw_created:
        if _raw.datum != record:
            _msg = f'hash collision!?\n===\n{_raw.datum}\n===\n{record}'
            logger.critical(_msg)
            sentry_sdk.capture_message(_msg)
        _raw.mediatype = record_mediatype
        # keep the latest datestamp
        if (not _raw.datestamp) or (_raw.datestamp < _datestamp):
            _raw.datestamp = _datestamp
        _raw.save(update_fields=('mediatype', 'datestamp'))
    _schedule_ingest(_suid)


def _schedule_ingest(suid):
    # TODO: clean up this path (circular imports suggest badly organized)
    from share.ingest.scheduler import IngestScheduler
    _ingest_job = IngestScheduler().schedule(suid, claim=True)
    from share.tasks import ingest
    ingest.delay(job_id=_ingest_job.id, exhaust=False)


def extract(raw: share_db.RawDatum) -> list[trove_db.RdfIndexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    will create (or update):
        RdfIndexcard (all extracted metadata)
        DerivedIndexcard (formatted version of RdfIndexcard)
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.PersistentIri equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _tripledict: gather.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    _cards = []
    for _focus_piri in raw.suid.record_focus_piri_set.all():
        _focus_iri = _focus_piri.find_equivalent_iri(_tripledict)
        # TODO handle _focus_iri not found
        # TODO if not _tripledict: raw.save(update_fields=['no_output'])
        _cards.append(trove_db.RdfIndexcard.objects.save_indexcard(
            from_raw_datum=raw,
            focus_iri=_focus_iri,
            tripledict=_tripledict,
        ))
        # any iri that has the focus iri as prefix is interpreted as a separate vocab term
        for _iri, _twopledict in _tripledict.items():
            if _iri.startswith(_focus_iri) and (_iri != _focus_iri):
                _cards.append(trove_db.RdfIndexcard.objects.save_indexcard(
                    from_raw_datum=raw,
                    focus_iri=_iri,
                    tripledict={_iri: _twopledict},
                ))
    # TODO: DerivedIndexcards
    return _cards


def excrete(suid, *, urgent: bool, index_messenger=None):
    '''excrete: send extracted index card to every public search index
    '''
    _index_messenger = index_messenger or IndexMessenger()
    _index_messenger.send_message(MessageType.INDEX_SUID, [suid.id], urgent=urgent)
