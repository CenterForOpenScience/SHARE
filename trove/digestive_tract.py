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
from gather import primitive_rdf

from share import models as share_db
from share.search import IndexMessenger, MessageType
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.exceptions import DigestiveError
from trove.extract import get_rdf_extractor_class
from trove.derive import get_deriver_classes
from trove.vocab.namespaces import RDFS


logger = logging.getLogger(__name__)


@transaction.atomic
def swallow(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    record_mediatype: typing.Optional[str],  # passing None indicates sharev2 backcompat
    focus_iri: str,
    datestamp=None,  # default "now"
    urgent=False,
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
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.update_or_create(
        source_config=_source_config,
        identifier=record_identifier,
    )
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
        datestamp=datestamp,
    )
    _task = task__extract_and_derive.delay(_raw.id, urgent=urgent)
    return _task.id


@transaction.atomic
def swallow__sharev2_legacy(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    record: str,
    record_identifier: str,
    transformer_key: str,
    datestamp=None,  # default "now"
    urgent=False,
):
    _source_config = (
        share_db.SourceConfig.objects
        .get_or_create_push_config(from_user, transformer_key)
    )
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.update_or_create(
        source_config=_source_config,
        identifier=record_identifier,
    )
    _raw = share_db.RawDatum.objects.store_datum_for_suid(
        suid=_suid,
        datum=record,
        mediatype=None,  # indicate sharev2-legacy flow
        datestamp=datestamp,
    )
    _task = task__extract_and_derive.delay(_raw.id, urgent=urgent)
    return _task.id


def extract(raw: share_db.RawDatum, *, undelete_indexcards=False) -> list[trove_db.Indexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    will create (or update):
        ResourceIdentifier (for each described resource and its types)
        Indexcard (with identifiers and type-identifiers for each described resource)
        ArchivedIndexcardRdf (all extracted metadata)
        LatestIndexcardRdf (all extracted metadata, if latest raw)
    may delete:
        LatestIndexcardRdf (previously extracted from the record, but no longer present)
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize (or just validate) tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.ResourceIdentifier equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _extracted_tripledict: primitive_rdf.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    _tripledicts_by_focus_iri = {}
    if raw.mediatype is None:  # back-compat
        from trove.extract.legacy_sharev2 import LegacySharev2Extractor
        assert isinstance(_extractor, LegacySharev2Extractor)
        _focus_iri = _extractor.extracted_focus_iri
        if not _focus_iri:
            raise DigestiveError(f'could not extract focus_iri from (sharev2) {raw}')
        if not share_db.FeatureFlag.objects.flag_is_up(share_db.FeatureFlag.IGNORE_SHAREV2_INGEST):
            _sharev2_legacy_ingest(raw, _extractor.sharev2graph_centralnode)
    else:
        try:
            _focus_iri = raw.suid.focus_identifier.find_equivalent_iri(_extracted_tripledict)
        except ValueError:
            raise DigestiveError(f'could not find {raw.suid.focus_identifier} in {raw}')
    _tripledicts_by_focus_iri[_focus_iri] = _extracted_tripledict
    # special case: any subject iri prefixed by the focus iri gets
    # treated as a separate vocab term and gets its own index card
    # (TODO: consider a separate index card for each subject iri?)
    for _iri, _twopledict in _extracted_tripledict.items():
        if (_iri != _focus_iri) and _iri.startswith(_focus_iri):
            _term_tripledict = {_iri: copy.deepcopy(_twopledict)}
            primitive_rdf.TripledictWrapper(_term_tripledict).add_triple(
                (_iri, RDFS.isDefinedBy, _focus_iri),
            )
            _tripledicts_by_focus_iri[_iri] = _term_tripledict
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
    if indexcard.deleted or not indexcard.latest_indexcard_rdf:
        return
    for _deriver_class in get_deriver_classes(deriver_iris):
        _deriver = _deriver_class(upriver_rdf=indexcard.latest_indexcard_rdf)
        _deriver_identifier = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            trove_db.DerivedIndexcard.objects.filter(
                upriver_indexcard=indexcard,
                deriver_identifier=_deriver_identifier,
            ).delete()
        else:
            _derived_text = _deriver.derive_card_as_text()
            _derived_checksum_iri = ChecksumIri.digest('sha-256', salt='', raw_data=_derived_text)
            trove_db.DerivedIndexcard.objects.update_or_create(
                upriver_indexcard=indexcard,
                deriver_identifier=_deriver_identifier,
                defaults={
                    'derived_text': _deriver.derive_card_as_text(),
                    'derived_checksum_iri': _derived_checksum_iri,
                },
            )


def expel(from_user: share_db.ShareUser, record_identifier: str):
    _suid_qs = share_db.SourceUniqueIdentifier.objects.filter(
        source_config__source__user=from_user,
        identifier=record_identifier,
    )
    for _indexcard in trove_db.Indexcard.objects.filter(source_record_suid__in=_suid_qs):
        _indexcard.pls_delete()
        notify_indexcard_update(_indexcard, urgent=True)


### BEGIN celery tasks

@celery.shared_task(acks_late=True, bind=True)
def task__extract_and_derive(task: celery.Task, raw_id: int, urgent=False):
    _raw = share_db.RawDatum.objects.select_related('suid').get(id=raw_id)
    _indexcards = extract(_raw, undelete_indexcards=urgent)
    if _raw.is_latest():
        for _indexcard in _indexcards:
            derive(_indexcard)
            notify_indexcard_update(_indexcard, celery_app=task.app, urgent=urgent)


@celery.shared_task(acks_late=True, bind=True)
def task__derive(task: celery.Task, indexcard_id: int, deriver_iri: str):
    _indexcard = trove_db.Indexcard.objects.get(id=indexcard_id)
    derive(_indexcard, deriver_iris=[deriver_iri])
    # TODO: avoid unnecessary work; let IndexStrategy subscribe to a specific
    # IndexcardDeriver (perhaps by deriver-specific MessageType?)
    notify_indexcard_update(_indexcard, celery_app=task.app)


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
def task__schedule_all_for_deriver(deriver_iri: str):
    if not get_deriver_classes([deriver_iri]):
        raise DigestiveError(f'unknown deriver_iri: {deriver_iri}')
    _indexcard_id_qs = (
        trove_db.Indexcard.objects
        .values_list('id', flat=True)
    )
    for _indexcard_id in _indexcard_id_qs.iterator():
        task__derive.apply_async((_indexcard_id, deriver_iri))


def notify_indexcard_update(indexcard, *, celery_app=None, urgent=False):
    _index_messenger = IndexMessenger(celery_app=celery_app)
    _index_messenger.send_message(MessageType.UPDATE_INDEXCARD, indexcard.id, urgent=urgent)


def notify_suid_update(suid_id, *, celery_app=None, urgent=False):
    _index_messenger = IndexMessenger(celery_app=celery_app)
    _index_messenger.send_message(MessageType.INDEX_SUID, suid_id, urgent=urgent)


# TODO: remove legacy ingest
def _sharev2_legacy_ingest(raw_datum, sharev2graph_centralnode):
    _normd = share_db.NormalizedData.objects.create(
        data=sharev2graph_centralnode.graph.to_jsonld(),
        source=raw_datum.suid.source_config.source.user,
        raw=raw_datum,
    )
    share_db.FormattedMetadataRecord.objects.save_formatted_records(
        raw_datum.suid,
        normalized_datum=_normd,
    )