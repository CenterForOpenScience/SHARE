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
from django.db.models import Q
import gather
import sentry_sdk

from share import models as share_db
from share.search import IndexMessenger, MessageType
from trove import models as trove_db
from trove.exceptions import DigestiveError
from trove.extract import get_rdf_extractor_class
from trove.derive import get_deriver_classes
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
    urgent=False,
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
    _resource_identifier = (
        trove_db.ResourceIdentifier.objects.get_or_create_for_iri(resource_iri)
        if resource_iri is not None
        else None
    )
    _suid, _suid_created = share_db.SourceUniqueIdentifier.objects.update_or_create(
        source_config=_source_config,
        identifier=record_identifier,
        defaults={
            'resource_identifier': _resource_identifier
        },
    )
    _raw = share_db.RawDatum.objects.store_datum_for_suid(
        suid=_suid,
        datum=record,
        mediatype=record_mediatype,
        datestamp=datestamp,
    )
    task__extract_and_derive.delay(_raw.id, urgent=True)


def extract(raw: share_db.RawDatum) -> list[trove_db.RdfIndexcard]:
    '''extract: gather rdf graph from a record; store as index card(s)

    will create (or update):
        RdfIndexcard (all extracted metadata)
        ResourceIdentifier (for each indexcard focus iri and its types)
    will delete:
        RdfIndexcard (any previously extracted from the record)
    '''
    _extractor = get_rdf_extractor_class(raw.mediatype)(raw.suid.source_config)
    # TODO normalize (or just validate) tripledict:
    #   - synonymous iris should be grouped (only one as subject-key, others under owl:sameAs)
    #   - focus should have rdf:type
    #   - no subject-key iris which collide by trove_db.ResourceIdentifier equivalence
    #   - connected graph (all subject-key iris reachable from focus, or reverse for vocab terms?)
    _extracted_tripledict: gather.RdfTripleDictionary = _extractor.extract_rdf(raw.datum)
    _tripledicts_by_focus_iri = {}
    if raw.suid.resource_identifier is None:  # back-compat
        from trove.extract.legacy_sharev2 import LegacySharev2Extractor
        assert isinstance(_extractor, LegacySharev2Extractor)
        _focus_iri = _extractor.extracted_focus_iri
        if not _focus_iri:
            raise DigestiveError(f'could not extract focus_iri from (sharev2) {raw}')
    else:
        try:
            _focus_iri = raw.suid.resource_identifier.find_equivalent_iri(_extracted_tripledict)
        except ValueError:
            raise DigestiveError(f'could not find {raw.suid.resource_identifier} in {raw}')
    _tripledicts_by_focus_iri[_focus_iri] = _extracted_tripledict
    # special case: any subject iri prefixed by the focus iri gets
    # treated as a separate vocab term and gets its own index card
    for _iri, _twopledict in _extracted_tripledict.items():
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
    _deriver_classes = get_deriver_classes(deriver_iris)
    _suid = indexcard.get_suid()
    for _deriver_class in _deriver_classes:
        _deriver = _deriver_class(upriver_card=indexcard)
        _deriver_identifier = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_deriver.deriver_iri())
        if _deriver.should_skip():
            trove_db.DerivedIndexcard.objects.filter(
                suid=_suid,
                deriver_identifier=_deriver_identifier,
            ).delete()
        else:
            trove_db.DerivedIndexcard.objects.update_or_create(
                suid=_suid,
                deriver_identifier=_deriver_identifier,
                defaults={
                    'upriver_card': indexcard,
                    'card_as_text': _deriver.derive_card_as_text(),
                },
            )


### BEGIN celery tasks

@celery.shared_task(acks_late=True, bind=True)
def task__extract_and_derive(task: celery.Task, raw_id: int, urgent=False, known_old=False):
    _raw = share_db.RawDatum.objects.select_related('suid').get(id=raw_id)
    if not known_old:
        _most_recent_raw_id = _raw.suid.most_recent_raw_datum_id()
        if _raw.id != _most_recent_raw_id:
            _msg = f'skipping extract of {_raw} (more recent: id={_most_recent_raw_id})'
            logger.warning(_msg)
            sentry_sdk.capture_message(_msg)
            return
    _indexcards = extract(_raw)
    for _indexcard in _indexcards:
        derive(_indexcard)
    notify_suid_update(_raw.suid_id, celery_app=task.app, urgent=urgent)


@celery.shared_task(acks_late=True, bind=True)
def task__derive(task: celery.Task, indexcard_id: int, deriver_iri: str):
    _indexcard = trove_db.RdfIndexcard.objects.get(id=indexcard_id)
    derive(_indexcard, deriver_iris=[deriver_iri])


@celery.shared_task(acks_late=True)
def task__schedule_extract_and_derive_for_source_config(source_config_id: int):
    _raw_id_qs = (
        share_db.RawDatum.objects
        .latest_by_suid_filter(Q(source_config_id=source_config_id))
        .values_list('id', flat=True)
    )
    for _raw_id in _raw_id_qs.iterator():
        task__extract_and_derive.delay(_raw_id)


@celery.shared_task(acks_late=True)
def task__schedule_all_for_deriver(deriver_iri: str):
    if not get_deriver_classes([deriver_iri]):
        raise DigestiveError(f'unknown deriver_iri: {deriver_iri}')
    _raw_id_qs = (
        share_db.RawDatum.objects
        .latest_by_suid_filter(Q(raw_data__rdf_indexcard_set__isnull=False))
        .values('id')
    )
    _indexcard_id_qs = (
        trove_db.RdfIndexcard.objects
        .filter(from_raw_datum_id__in=_raw_id_qs)
        .values_list('id', flat=True)
    )
    for _indexcard_id in _indexcard_id_qs.iterator():
        task__derive.apply_async((_indexcard_id, deriver_iri))


def notify_suid_update(suid_id, *, celery_app=None, urgent=False):
    _index_messenger = IndexMessenger(celery_app=celery_app)
    _index_messenger.send_message(MessageType.INDEX_SUID, suid_id, urgent=urgent)
