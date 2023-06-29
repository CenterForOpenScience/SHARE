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
import sentry_sdk

from share.exceptions import IngestError
from share import models as share_db
from trove import models as trove_db
from trove.extract import get_rdf_extractor_class
from trove.derive import INDEXCARD_DERIVERS


logger = logging.getLogger(__name__)


@transaction.atomic
def swallow(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    record_mediatype: str,
    resource_iri: str,
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
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.update_or_create(
        source_config=_source_config,
        identifier=record_identifier,
        defaults={
            'resource_piri': trove_db.PersistentIri.objects.get_or_create_for_iri(resource_iri),
        },
    )
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
        PersistentIri (for each indexcard focus iri and its types)
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.PersistentIri equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _tripledict: gather.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    # TODO if not _tripledict: raw.save(update_fields=['no_output'])
    _focus_iri = raw.suid.resource_piri.find_equivalent_iri(_tripledict)
    # TODO handle _focus_iri not found
    _tripledicts_by_focus_iri = {_focus_iri: _tripledict}
    # any iri that has the focus iri as prefix is interpreted as a separate vocab term
    for _iri, _twopledict in _tripledict.items():
        if (_iri != _focus_iri) and _iri.startswith(_focus_iri):
            _tripledicts_by_focus_iri[_iri] = {_iri: _twopledict}
    _indexcards = trove_db.RdfIndexcard.objects.save_indexcards_for_raw_datum(
        from_raw_datum=raw,
        tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
    )
    return _indexcards


def excrete(indexcard: trove_db.RdfIndexcard):
    '''excrete: derive special-purpose index card(s) from an extracted index card
    '''
    for _deriver_class in INDEXCARD_DERIVERS:
        _deriver = _deriver_class(indexcard)
        _deriver_piri = trove_db.PersistentIri.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            logger.info(f'excrete: skipping {_deriver} for {indexcard}')
            trove_db.DerivedIndexcard.objects.filter(
                upriver_card=indexcard,
                deriver_piri=_deriver_piri,
            ).delete()
        else:
            logger.info(f'excrete: invoking {_deriver} for {indexcard}')
            trove_db.DerivedIndexcard.objects.update_or_create(
                upriver_card=indexcard,
                deriver_piri=_deriver_piri,
                defaults={
                    'card_as_text': _deriver.derive_card_as_text(),
                },
            )
