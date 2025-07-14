'''a small interface for ingesting metadata records

leaning (perhaps too far) into "ingest" as metaphor

sniff: set up identifiers about a record
extract: gather rdf graph from a record; store as index card(s)
derive: build other representations from latest card version(s)
'''
__all__ = ('sniff', 'extract', 'derive', 'expel', 'ingest')

import copy
import datetime
import logging
from typing import Iterable

import celery
from django.db import transaction
from django.db.models import QuerySet
from primitive_metadata import primitive_rdf

from share import models as share_db
from share.search import IndexMessenger
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.exceptions import (
    CannotDigestExpiredDatum,
    DigestiveError,
)
from trove.extract import get_rdf_extractor_class
from trove.derive import get_deriver_classes
from trove.util.iris import smells_like_iri
from trove.vocab.namespaces import RDFS, RDF, OWL


logger = logging.getLogger(__name__)


def ingest(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    focus_iri: str,
    record_mediatype: str,
    raw_record: str,
    record_identifier: str | None = None,  # default focus_iri
    is_supplementary: bool = False,
    expiration_date: datetime.date | None = None,  # default "never"
    restore_deleted: bool = False,
    urgent: bool = False,
) -> None:
    '''ingest: shorthand for sniff + extract + (eventual) derive'''
    _suid = sniff(
        from_user=from_user,
        record_identifier=record_identifier,
        focus_iri=focus_iri,
        is_supplementary=is_supplementary,
    )
    if _suid.source_config.disabled or _suid.source_config.source.is_deleted:
        expel_suid(_suid)
    else:
        _extracted_cards = extract(
            suid=_suid,
            record_mediatype=record_mediatype,
            raw_record=raw_record,
            restore_deleted=restore_deleted,
            expiration_date=expiration_date,
        )
        for _card in _extracted_cards:
            task__derive.delay(_card.pk, urgent=urgent)


@transaction.atomic
def sniff(
    *,  # all keyword-args
    from_user: share_db.ShareUser,
    focus_iri: str,
    record_identifier: str | None = None,
    is_supplementary: bool = False,
) -> share_db.SourceUniqueIdentifier:
    '''sniff: get a vague sense of a metadata record without touching the record itself

    ensures in the database:
        * `share.models.Source`/`SourceConfig` for given `from_user`, with...
        * `share.models.SourceUniqueIdentifier` for given `record_identifier`, with...
        * `trove.models.ResourceIdentifier` for given `focus_iri`

    returns the `SourceUniqueIdentifier`, as the center of that constellation

    for a given `(from_user, record_identifier)` pair, `focus_iri` and `is_supplementary`
    must not change -- raises `DigestiveError` if called again with different values
    '''
    if not smells_like_iri(focus_iri):
        raise DigestiveError(f'invalid focus_iri "{focus_iri}"')
    if is_supplementary and not record_identifier:
        raise DigestiveError(f'supplementary records must have non-empty record_identifier! focus_iri={focus_iri} from_user={from_user}')
    if is_supplementary and (record_identifier == focus_iri):
        raise DigestiveError(f'supplementary records must have record_identifier distinct from their focus! focus_iri={focus_iri} record_identifier={record_identifier} from_user={from_user}')
    _source_config = share_db.SourceConfig.objects.get_or_create_push_config(from_user)
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.get_or_create(
        source_config=_source_config,
        identifier=record_identifier or focus_iri,
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
        if _suid.focus_identifier_id != _focus_identifier.pk:
            raise DigestiveError(f'suid focus_identifier should not change! suid={_suid}, focus changed from {_suid.focus_identifier} to {_focus_identifier}')
    return _suid


def extract(
    suid: share_db.SourceUniqueIdentifier,
    record_mediatype: str,
    raw_record: str,
    *,
    expiration_date: datetime.date | None = None,  # default "never"
    restore_deleted: bool = False,
) -> list[trove_db.Indexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    may create (or update):
        ResourceIdentifier (for each described resource and its types)
        Indexcard (with identifiers and type-identifiers for each described resource)
        ArchivedResourceDescription (all extracted metadata, if non-supplementary)
        LatestResourceDescription (all extracted metadata, if latest raw and non-supplementary)
        SupplementaryResourceDescription (all extracted metadata, if supplementary)
    may delete:
        LatestResourceDescription (previously extracted from the record, but no longer present)
    '''
    if (expiration_date is not None) and (expiration_date <= datetime.date.today()):
        raise CannotDigestExpiredDatum(suid, expiration_date)
    _tripledicts_by_focus_iri = {}
    _extractor = get_rdf_extractor_class(record_mediatype)()
    # TODO normalize (or just validate) tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.ResourceIdentifier equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _extracted_tripledict: primitive_rdf.RdfTripleDictionary = _extractor.extract_rdf(raw_record)
    if _extracted_tripledict:
        assert suid.focus_identifier is not None
        try:
            _focus_iri = suid.focus_identifier.find_equivalent_iri(_extracted_tripledict)
        except ValueError:
            raise DigestiveError(f'could not find {suid.focus_identifier} in """{raw_record}"""')
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
    if suid.is_supplementary:
        return trove_db.Indexcard.objects.supplement_indexcards_from_tripledicts(
            supplementary_suid=suid,
            rdf_tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
            expiration_date=expiration_date,
        )
    return trove_db.Indexcard.objects.save_indexcards_from_tripledicts(
        suid=suid,
        rdf_tripledicts_by_focus_iri=_tripledicts_by_focus_iri,
        restore_deleted=restore_deleted,
        expiration_date=expiration_date,
    )


def derive(indexcard: trove_db.Indexcard, deriver_iris: Iterable[str] | None = None) -> list[trove_db.DerivedIndexcard]:
    '''derive: build other kinds of index cards from the extracted rdf

    will create, update, or delete:
        DerivedIndexcard
    '''
    if indexcard.deleted:
        return []
    try:
        _latest_resource_description = indexcard.latest_resource_description
    except trove_db.LatestResourceDescription.DoesNotExist:
        return []
    _derived_list = []
    for _deriver_class in get_deriver_classes(deriver_iris):
        _deriver = _deriver_class(upstream_description=_latest_resource_description)
        _deriver_identifier = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            trove_db.DerivedIndexcard.objects.filter(
                upriver_indexcard=indexcard,
                deriver_identifier=_deriver_identifier,
            ).delete()
        else:
            _derived_text = _deriver.derive_card_as_text()
            _derived_checksum_iri = ChecksumIri.digest('sha-256', salt='', data=_derived_text)
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


def expel(from_user: share_db.ShareUser, record_identifier: str) -> None:
    _suid_qs = share_db.SourceUniqueIdentifier.objects.filter(
        source_config__source__user=from_user,
        identifier=record_identifier,
    )
    for _suid in _suid_qs:
        expel_suid(_suid)


def expel_suid(suid: share_db.SourceUniqueIdentifier) -> None:
    for _indexcard in trove_db.Indexcard.objects.filter(source_record_suid=suid):
        _indexcard.pls_delete()
    _expel_supplementary_descriptions(
        trove_db.SupplementaryResourceDescription.objects.filter(supplementary_suid=suid),
    )


def expel_expired_data(today: datetime.date) -> None:
    # mark indexcards deleted if their latest update has now expired
    for _indexcard in trove_db.Indexcard.objects.filter(
        trove_latestresourcedescription_set__expiration_date__lte=today,
    ):
        _indexcard.pls_delete()
    # delete expired supplementary metadata
    _expel_supplementary_descriptions(
        trove_db.SupplementaryResourceDescription.objects.filter(expiration_date__lte=today),
    )


def _expel_supplementary_descriptions(supplementary_rdf_queryset: QuerySet[trove_db.SupplementaryResourceDescription]) -> None:
    # delete expired supplementary metadata
    _affected_indexcards = set()
    for _supplement in supplementary_rdf_queryset.select_related('indexcard'):
        if not _supplement.indexcard.deleted:
            _affected_indexcards.add(_supplement.indexcard)
        _supplement.delete()
    for _indexcard in _affected_indexcards:
        task__derive.delay(_indexcard.pk)


### BEGIN celery tasks

@celery.shared_task(acks_late=True, bind=True)
def task__derive(
    task: celery.Task,
    indexcard_id: int,
    deriver_iri: str | None = None,
    notify_index: bool = True,
    urgent: bool = False,
) -> None:
    _indexcard = trove_db.Indexcard.objects.get(id=indexcard_id)
    derive(
        _indexcard,
        deriver_iris=(None if deriver_iri is None else [deriver_iri]),
    )
    # TODO: avoid unnecessary work; let IndexStrategy subscribe to a specific
    # IndexcardDeriver (perhaps by deriver-specific MessageType?)
    if notify_index:
        IndexMessenger(celery_app=task.app).notify_indexcard_update([_indexcard], urgent=urgent)


@celery.shared_task(acks_late=True)
def task__schedule_derive_for_source_config(source_config_id: int, notify_index: bool = False) -> None:
    _indexcard_id_qs = (
        trove_db.Indexcard.objects
        .filter(source_record_suid__source_config_id=source_config_id)
        .values_list('id', flat=True)
    )
    for _indexcard_id in _indexcard_id_qs.iterator():
        task__derive.delay(_indexcard_id, notify_index=notify_index)


@celery.shared_task(acks_late=True)
def task__schedule_all_for_deriver(deriver_iri: str, notify_index: bool = False) -> None:
    if not get_deriver_classes([deriver_iri]):
        raise DigestiveError(f'unknown deriver_iri: {deriver_iri}')
    _indexcard_id_qs = (
        trove_db.Indexcard.objects
        .values_list('id', flat=True)
    )
    for _indexcard_id in _indexcard_id_qs.iterator():
        task__derive.apply_async((_indexcard_id, deriver_iri, notify_index))


@celery.shared_task(acks_late=True)
def task__expel_expired_data() -> None:
    expel_expired_data(datetime.date.today())
