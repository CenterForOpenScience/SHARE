'''a small interface for ingesting metadata records

leaning (perhaps too far) into "ingest" as metaphor

swallow: store a given record by checksum; queue for extraction
extract: gather rdf graph from a record; store as index card(s)
derive: build other kinds of index cards from the extracted rdf
'''
__all__ = ('swallow', 'extract', 'derive')

import copy
import datetime
import logging

import celery
from django.db import transaction
from primitive_metadata import primitive_rdf

from share import models as share_db
from share.search import IndexMessenger
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.exceptions import (
    CannotDigestExpiredDatum,
    DigestiveError,
    MissingMediatype,
)
from trove.extract import get_rdf_extractor_class
from trove.derive import get_deriver_classes
from trove.vocab.namespaces import RDFS, RDF, OWL


logger = logging.getLogger(__name__)


@transaction.atomic
def swallow(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    record_mediatype: str | None,  # passing None indicates sharev2 backcompat
    focus_iri: str,
    datestamp: datetime.datetime | None = None,  # default "now"
    expiration_date: datetime.date | None = None,
    urgent: bool = False,
    is_supplementary: bool = False,
):
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
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.get_or_create(
        source_config=_source_config,
        identifier=record_identifier,
        defaults={
            'is_supplementary': is_supplementary,
        },
    )
    if bool(_suid.is_supplementary) != is_supplementary:
        raise DigestiveError(f'suid is_supplementary should not change! suid={_suid}, is_supplementary changed from {bool(_suid.is_supplementary)} to {is_supplementary}')
    _focus_identifier = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(focus_iri)
    if _suid.focus_identifier is None:
        _suid.focus_identifier = _focus_identifier
        _suid.save()
    else:
        if _suid.focus_identifier_id != _focus_identifier.id:
            raise DigestiveError(f'suid focus_identifier should not change! suid={_suid}, focus changed from {_suid.focus_identifier} to {_focus_identifier}')
    _raw = share_db.RawDatum.objects.store_datum_for_suid(
        suid=_suid,
        datum=record,
        mediatype=record_mediatype,
        datestamp=(datestamp or datetime.datetime.now(tz=datetime.timezone.utc)),
        expiration_date=expiration_date,
    )
    _task = task__extract_and_derive.delay(_raw.id, urgent=urgent)
    return _task.id


def extract(raw: share_db.RawDatum, *, undelete_indexcards=False) -> list[trove_db.Indexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    may create (or update):
        ResourceIdentifier (for each described resource and its types)
        Indexcard (with identifiers and type-identifiers for each described resource)
        ArchivedIndexcardRdf (all extracted metadata, if non-supplementary)
        LatestIndexcardRdf (all extracted metadata, if latest raw and non-supplementary)
        SupplementaryIndexcardRdf (all extracted metadata, if supplementary)
    may delete:
        LatestIndexcardRdf (previously extracted from the record, but no longer present)
    '''
    assert raw.mediatype is not None, 'raw datum has no mediatype -- did you mean to call extract_legacy?'
    if raw.is_expired:
        raise CannotDigestExpiredDatum(raw)
    _tripledicts_by_focus_iri = {}
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize (or just validate) tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.ResourceIdentifier equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _extracted_tripledict: primitive_rdf.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    if _extracted_tripledict:
        try:
            _focus_iri = raw.suid.focus_identifier.find_equivalent_iri(_extracted_tripledict)
        except ValueError:
            raise DigestiveError(f'could not find {raw.suid.focus_identifier} in {raw}')
        _tripledicts_by_focus_iri[_focus_iri] = _extracted_tripledict
        # special case: if the record defines an ontology, create a
        # card for each subject iri that starts with the focus iri
        # (TODO: consider a separate index card for *every* subject iri?)
        if OWL.Ontology in _extracted_tripledict.get(_focus_iri, {}).get(RDF.type, ()):
            for _iri, _twopledict in _extracted_tripledict.items():
                if (_iri != _focus_iri) and _iri.startswith(_focus_iri):
                    _term_tripledict = {_iri: copy.deepcopy(_twopledict)}
                    # ensure a link to the ontology (in case there's not already)
                    primitive_rdf.RdfGraph(_term_tripledict).add(
                        (_iri, RDFS.isDefinedBy, _focus_iri),
                    )
                    _tripledicts_by_focus_iri[_iri] = _term_tripledict
    if raw.suid.is_supplementary:
        return trove_db.Indexcard.objects.supplement_indexcards_from_tripledicts(
            from_raw_datum=raw,
            rdf_tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
        )
    return trove_db.Indexcard.objects.save_indexcards_from_tripledicts(
        from_raw_datum=raw,
        rdf_tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
        undelete=undelete_indexcards,
    )


def derive(indexcard: trove_db.Indexcard, deriver_iris=None):
    '''derive: build other kinds of index cards from the extracted rdf

    will create, update, or delete:
        DerivedIndexcard
    '''
    if indexcard.deleted:
        return []
    try:
        _latest_rdf = indexcard.latest_rdf
    except trove_db.LatestIndexcardRdf.DoesNotExist:
        return []
    _derived_list = []
    for _deriver_class in get_deriver_classes(deriver_iris):
        _deriver = _deriver_class(upriver_rdf=_latest_rdf)
        _deriver_identifier = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            trove_db.DerivedIndexcard.objects.filter(
                upriver_indexcard=indexcard,
                deriver_identifier=_deriver_identifier,
            ).delete()
        else:
            _derived_text = _deriver.derive_card_as_text()
            _derived_checksum_iri = ChecksumIri.digest('sha-256', salt='', raw_data=_derived_text)
            _derived, _ = trove_db.DerivedIndexcard.objects.update_or_create(
                upriver_indexcard=indexcard,
                deriver_identifier=_deriver_identifier,
                defaults={
                    'derived_text': _derived_text,
                    'derived_checksum_iri': _derived_checksum_iri,
                },
            )
            _derived_list.append(_derived)
    return _derived_list


def expel(from_user: share_db.ShareUser, record_identifier: str):
    _suid_qs = share_db.SourceUniqueIdentifier.objects.filter(
        source_config__source__user=from_user,
        identifier=record_identifier,
    )
    for _suid in _suid_qs:
        expel_suid(_suid)


def expel_suid(suid: share_db.SourceUniqueIdentifier) -> None:
    for _indexcard in trove_db.Indexcard.objects.filter(source_record_suid=suid):
        _indexcard.pls_delete()
    _expel_supplementary_rdf(
        trove_db.SupplementaryIndexcardRdf.objects.filter(supplementary_suid=suid),
    )


def expel_expired_data(today: datetime.date) -> None:
    # mark indexcards deleted if their latest update has now expired
    for _indexcard in trove_db.Indexcard.objects.filter(
        trove_latestindexcardrdf_set__from_raw_datum__expiration_date__lte=today,
    ):
        _indexcard.pls_delete()
    # delete expired supplementary metadata
    _expel_supplementary_rdf(
        trove_db.SupplementaryIndexcardRdf.objects.filter(
            from_raw_datum__expiration_date__lte=today,
        ),
    )


def _expel_supplementary_rdf(supplementary_rdf_queryset) -> None:
    # delete expired supplementary metadata
    _affected_indexcards = set()
    for _supplementary_rdf in supplementary_rdf_queryset.select_related('indexcard'):
        if not _supplementary_rdf.indexcard.deleted:
            _affected_indexcards.add(_supplementary_rdf.indexcard)
        _supplementary_rdf.delete()
    for _indexcard in _affected_indexcards:
        task__derive.delay(_indexcard.id)


### BEGIN celery tasks

@celery.shared_task(acks_late=True, bind=True)
def task__extract_and_derive(task: celery.Task, raw_id: int, urgent=False):
    _raw = (
        share_db.RawDatum.objects
        .select_related('suid__source_config__source')
        .get(id=raw_id)
    )
    _source_config = _raw.suid.source_config
    if _source_config.disabled or _source_config.source.is_deleted:
        expel_suid(_raw.suid)
    else:
        if not _raw.mediatype:
            raise MissingMediatype(_raw)
        _indexcards = extract(_raw, undelete_indexcards=urgent)
        if _raw.is_latest():
            _messenger = IndexMessenger(celery_app=task.app)
            for _indexcard in _indexcards:
                derive(_indexcard)
            _messenger.notify_indexcard_update(_indexcards, urgent=urgent)


@celery.shared_task(acks_late=True, bind=True)
def task__derive(
    task: celery.Task,
    indexcard_id: int,
    deriver_iri: str | None = None,
    notify_index=True,
):
    _indexcard = trove_db.Indexcard.objects.get(id=indexcard_id)
    derive(
        _indexcard,
        deriver_iris=(None if deriver_iri is None else [deriver_iri]),
    )
    # TODO: avoid unnecessary work; let IndexStrategy subscribe to a specific
    # IndexcardDeriver (perhaps by deriver-specific MessageType?)
    if notify_index:
        IndexMessenger(celery_app=task.app).notify_indexcard_update([_indexcard])


@celery.shared_task(acks_late=True)
def task__schedule_extract_and_derive_for_source_config(source_config_id: int):
    _raw_id_qs = (
        share_db.RawDatum.objects
        .latest_by_suid_queryset(
            share_db.SourceUniqueIdentifier.objects
            .filter(source_config_id=source_config_id)
        )
        .values_list('id', flat=True)
    )
    for _raw_id in _raw_id_qs.iterator():
        task__extract_and_derive.delay(_raw_id)


@celery.shared_task(acks_late=True)
def task__schedule_all_for_deriver(deriver_iri: str, notify_index=False):
    if not get_deriver_classes([deriver_iri]):
        raise DigestiveError(f'unknown deriver_iri: {deriver_iri}')
    _indexcard_id_qs = (
        trove_db.Indexcard.objects
        .values_list('id', flat=True)
    )
    for _indexcard_id in _indexcard_id_qs.iterator():
        task__derive.apply_async((_indexcard_id, deriver_iri, notify_index))


@celery.shared_task(acks_late=True)
def task__expel_expired_data():
    expel_expired_data(datetime.date.today())
