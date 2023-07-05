'''a small interface for ingesting metadata records

leaning (perhaps too far) into "ingest" as metaphor

swallow: store a given record by checksum; queue for extraction
extract: gather rdf graph from a record; store as index card(s)
derive: build other kinds of index cards from the extracted rdf
'''
__all__ = ('swallow', 'extract', 'derive')

import copy
import logging
import typing

import celery
from django.db import transaction
import gather

from share import models as share_db
from trove import models as trove_db
from trove.exceptions import DigestiveError
from trove.extract import get_rdf_extractor_class
from trove.derive import DERIVER_SET
from trove.vocab import RDFS


logger = logging.getLogger(__name__)


@transaction.atomic
def swallow(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    record_mediatype: typing.Optional[str],  # passing None indicates sharev2 backcompat
    resource_iri: typing.Optional[str],  # may be None only if record_mediatype=None
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
        raise DigestiveError('datum must be a string')
    _source_config = share_db.SourceConfig.objects.get_or_create_push_config(from_user)
    if record_mediatype is not None and resource_iri is None:
        raise DigestiveError('resource_iri required')
    _resource_piri = (
        trove_db.PersistentIri.objects.get_or_create_for_iri(resource_iri)
        if resource_iri is not None
        else None
    )
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.update_or_create(
        source_config=_source_config,
        identifier=record_identifier,
        defaults={
            'resource_piri': _resource_piri
        },
    )
    share_db.RawDatum.objects.store_datum_for_suid(
        suid=_suid,
        datum=record,
        mediatype=record_mediatype,
        datestamp=datestamp,
    )
    return _schedule_ingest(_suid)


def _schedule_ingest(suid) -> share_db.IngestJob:
    # TODO: clean up this path (circular imports suggest badly organized)
    from share.ingest.scheduler import IngestScheduler
    _ingest_job = IngestScheduler().schedule(suid, claim=True)
    from share.tasks import ingest
    ingest.delay(job_id=_ingest_job.id, exhaust=False)
    return _ingest_job


def extract(raw: share_db.RawDatum) -> list[trove_db.RdfIndexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    will create (or update):
        RdfIndexcard (all extracted metadata)
        PersistentIri (for each indexcard focus iri and its types)
    will delete:
        RdfIndexcard (any previously extracted from the record)
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.PersistentIri equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _tripledict: gather.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    try:
        _focus_iri = raw.suid.resource_piri.find_equivalent_iri(_tripledict)
    except ValueError:
        _tripledicts_by_focus_iri = {}
    else:
        _tripledicts_by_focus_iri = {_focus_iri: _tripledict}
        # special case: any subject iri prefixed by the focus iri gets
        # treated as a separate vocab term and gets its own index card
        for _iri, _twopledict in _tripledict.items():
            if (_iri != _focus_iri) and _iri.startswith(_focus_iri):
                _term_tripledict = {_iri: copy.deepcopy(_twopledict)}
                gather.add_triple_to_tripledict(
                    (_iri, RDFS.isDefinedBy, _focus_iri),
                    _term_tripledict,
                )
                _tripledicts_by_focus_iri[_iri] = _term_tripledict
    return trove_db.RdfIndexcard.objects.set_indexcards_for_raw_datum(
        from_raw_datum=raw,
        tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
    )


def derive(indexcard: trove_db.RdfIndexcard, deriver_iris=None):
    '''derive: build other kinds of index cards from the extracted rdf

    will create, update, or delete:
        DerivedIndexcard
    '''
    if deriver_iris is None:
        _deriver_classes = DERIVER_SET
    else:
        _deriver_classes = [
            _deriver_class
            for _deriver_class in DERIVER_SET
            if _deriver_class.deriver_iri() in deriver_iris
        ]
    _suid = indexcard.get_suid()
    for _deriver_class in _deriver_classes:
        _deriver = _deriver_class(upriver_card=indexcard)
        _deriver_piri = trove_db.PersistentIri.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            trove_db.DerivedIndexcard.objects.filter(
                suid=_suid,
                deriver_piri=_deriver_piri,
            ).delete()
        else:
            trove_db.DerivedIndexcard.objects.update_or_create(
                suid=_suid,
                deriver_piri=_deriver_piri,
                defaults={
                    'upriver_card': indexcard,
                    'card_as_text': _deriver.derive_card_as_text(),
                },
            )


### BEGIN celery tasks

@celery.shared_task(acks_late=True)
def task__extract_and_derive(suid_id: int):
    try:
        _raw = share_db.RawDatum.objects.latest_by_suid_ids([suid_id]).get()
    except share_db.RawDatum.DoesNotExist:
        logger.warning(f'RawDatum not found for suid_id={suid_id}')
    else:
        _indexcards = extract(_raw)
        for _indexcard in _indexcards:
            derive(_indexcard)


@celery.shared_task(acks_late=True)
def task__single_derive(suid_id: int, deriver_iri: str):
    try:
        _indexcard = (
            trove_db.RdfIndexcard.objects
            .latest_by_suid_ids([suid_id])
            .get()
        )
    except trove_db.RdfIndexcard.DoesNotExist:
        logger.warning(f'RdfIndexcard not found for suid_id={suid_id}')
    else:
        derive(_indexcard, deriver_iris=[deriver_iri])


@celery.shared_task(acks_late=True)
def task__schedule_extract_and_derive_for_source_config(source_config_id: int):
    _suid_id_qs = (
        share_db.SourceUniqueIdentifier.objects
        .filter(source_config_id=source_config_id)
        .values_list('id', flat=True)
    )
    for _id in _suid_id_qs.iterator():
        task__extract_and_derive.apply_async((_id,))


@celery.shared_task(acks_late=True)
def task__schedule_derive_all(deriver_iri: str):
    _suid_id_qs = (
        share_db.SourceUniqueIdentifier.objects
        .filter(raw_data__rdf_indexcard_set__isnull=False)
        .values_list('id', flat=True)
    )
    for _id in _suid_id_qs.iterator():
        task__single_derive.apply_async((_id, deriver_iri))
