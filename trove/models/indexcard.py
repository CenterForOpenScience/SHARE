from __future__ import annotations
import datetime
import uuid
from typing import Any

from django.db import models
from django.db import transaction
from django.utils import timezone
from primitive_metadata import primitive_rdf as rdf

from share import models as share_db  # TODO: break this dependency
from share.util.checksum_iri import ChecksumIri
from trove.exceptions import DigestiveError
from trove.models.derived_indexcard import DerivedIndexcard
from trove.models.resource_description import (
    ArchivedResourceDescription,
    ResourceDescription,
    LatestResourceDescription,
    SupplementaryResourceDescription,
)
from trove.models.resource_identifier import ResourceIdentifier
from trove.vocab.namespaces import RDF
from trove.vocab.trove import trove_indexcard_iri, trove_indexcard_namespace


__all__ = ('Indexcard',)


class IndexcardManager(models.Manager['Indexcard']):
    def get_for_iri(self, iri: str) -> Indexcard:
        _uuid = rdf.iri_minus_namespace(iri, namespace=trove_indexcard_namespace())
        return self.get(uuid=_uuid)

    @transaction.atomic
    def save_indexcards_from_tripledicts(
        self, *,
        suid: share_db.SourceUniqueIdentifier,
        rdf_tripledicts_by_focus_iri: dict[str, rdf.RdfTripleDictionary],
        restore_deleted: bool = False,
        expiration_date: datetime.date | None = None,
    ) -> list['Indexcard']:
        assert not suid.is_supplementary
        _indexcards = []
        _seen_focus_identifier_ids: set[str] = set()
        for _focus_iri, _tripledict in rdf_tripledicts_by_focus_iri.items():
            _indexcard = self.save_indexcard_from_tripledict(
                suid=suid,
                rdf_tripledict=_tripledict,
                focus_iri=_focus_iri,
                restore_deleted=restore_deleted,
                expiration_date=expiration_date,
            )
            _focus_identifier_ids = {str(_fid.pk) for _fid in _indexcard.focus_identifier_set.all()}
            if not _seen_focus_identifier_ids.isdisjoint(_focus_identifier_ids):
                _duplicates = (
                    ResourceIdentifier.objects
                    .filter(id__in=_seen_focus_identifier_ids.intersection(_focus_identifier_ids))
                )
                raise DigestiveError(f'duplicate focus iris: {list(_duplicates)}')
            _seen_focus_identifier_ids.update(_focus_identifier_ids)
            _indexcards.append(_indexcard)
        # cards seen previously on this suid (but not this time) treated as deleted
        for _indexcard_to_delete in (
            Indexcard.objects
            .filter(source_record_suid=suid)
            .exclude(id__in=[_card.pk for _card in _indexcards])
        ):
            _indexcard_to_delete.pls_delete()
            _indexcards.append(_indexcard_to_delete)
        return _indexcards

    @transaction.atomic
    def supplement_indexcards_from_tripledicts(
        self, *,
        supplementary_suid: share_db.SourceUniqueIdentifier,
        rdf_tripledicts_by_focus_iri: dict[str, rdf.RdfTripleDictionary],
        expiration_date: datetime.date | None = None,
    ) -> list[Indexcard]:
        assert supplementary_suid.is_supplementary
        _indexcards = []
        for _focus_iri, _tripledict in rdf_tripledicts_by_focus_iri.items():
            _indexcards.extend(self.supplement_indexcards(
                supplementary_suid=supplementary_suid,
                rdf_tripledict=_tripledict,
                focus_iri=_focus_iri,
                expiration_date=expiration_date,
            ))
        _seen_indexcard_ids = {_card.pk for _card in _indexcards}
        # supplementary data seen previously on this suid (but not this time) should be deleted
        for _supplement_to_delete in (
            SupplementaryResourceDescription.objects
            .filter(supplementary_suid=supplementary_suid)
            .exclude(indexcard__in=_indexcards)
        ):
            if _supplement_to_delete.indexcard_id not in _seen_indexcard_ids:
                _indexcards.append(_supplement_to_delete.indexcard)
            _supplement_to_delete.delete()
        return _indexcards

    @transaction.atomic
    def save_indexcard_from_tripledict(
        self, *,
        suid: share_db.SourceUniqueIdentifier,
        rdf_tripledict: rdf.RdfTripleDictionary,
        focus_iri: str,
        restore_deleted: bool = False,
        expiration_date: datetime.date | None = None,
    ) -> Indexcard:
        assert not suid.is_supplementary
        _focus_identifier_set = (
            ResourceIdentifier.objects
            .save_equivalent_identifier_set(rdf_tripledict, focus_iri)
        )
        _focustype_identifier_set = [  # TODO: require non-zero?
            ResourceIdentifier.objects.get_or_create_for_iri(_iri)
            for _iri in rdf_tripledict[focus_iri].get(RDF.type, ())
        ]
        _indexcard: Indexcard | None = Indexcard.objects.filter(
            source_record_suid=suid,
            focus_identifier_set__in=_focus_identifier_set,
        ).first()
        if _indexcard is None:
            _indexcard = Indexcard.objects.create(source_record_suid=suid)
        if restore_deleted and _indexcard.deleted:
            _indexcard.deleted = None
            _indexcard.save()
        _indexcard.focus_identifier_set.set(_focus_identifier_set)
        _indexcard.focustype_identifier_set.set(_focustype_identifier_set)
        _indexcard.update_resource_description(focus_iri, rdf_tripledict, expiration_date=expiration_date)
        return _indexcard

    @transaction.atomic
    def supplement_indexcards(
        self, *,
        supplementary_suid: share_db.SourceUniqueIdentifier,
        rdf_tripledict: rdf.RdfTripleDictionary,
        focus_iri: str,
        expiration_date: datetime.date | None = None,
    ) -> list[Indexcard]:
        assert supplementary_suid.is_supplementary
        # supplement indexcards with the same focus from the same source_config
        # (if none exist, fine, nothing gets supplemented)
        _indexcards = list(Indexcard.objects.filter(
            source_record_suid__source_config_id=supplementary_suid.source_config_id,
            focus_identifier_set__in=ResourceIdentifier.objects.queryset_for_iri(focus_iri),
        ))
        for _indexcard in _indexcards:
            _indexcard.update_supplementary_description(
                supplementary_suid=supplementary_suid,
                rdf_tripledict=rdf_tripledict,
                focus_iri=focus_iri,
                expiration_date=expiration_date,
            )
        return _indexcards


class Indexcard(models.Model):
    objects = IndexcardManager()
    # auto:
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)  # for public-api id
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # optional:
    deleted = models.DateTimeField(null=True, blank=True)

    # required:
    source_record_suid = models.ForeignKey(
        share_db.SourceUniqueIdentifier,
        on_delete=models.CASCADE,
        related_name='indexcard_set',
    )

    # focus_identifier_set should be non-overlapping for a given source_record_suid
    # (TODO: rework to get that enforceable with db constraints)
    focus_identifier_set = models.ManyToManyField(
        ResourceIdentifier,
        related_name='indexcard_set',
    )
    focustype_identifier_set = models.ManyToManyField(
        ResourceIdentifier,
        related_name='+',
    )

    class Meta:
        indexes = [
            models.Index(fields=('deleted',)),
        ]

    @property
    def latest_resource_description(self) -> LatestResourceDescription:
        '''convenience for the "other side" of LatestResourceDescription.indexcard
        '''
        return self.trove_latestresourcedescription_set.get()  # may raise DoesNotExist

    @property
    def archived_description_set(self) -> Any:
        '''convenience for the "other side" of ArchivedResourceDescription.indexcard

        returns a RelatedManager
        '''
        return self.trove_archivedresourcedescription_set

    @property
    def supplementary_description_set(self) -> Any:
        '''convenience for the "other side" of SupplementaryResourceDescription.indexcard

        returns a RelatedManager
        '''
        return self.trove_supplementaryresourcedescription_set

    def get_iri(self) -> str:
        return trove_indexcard_iri(self.uuid)

    def pls_delete(self, *, notify_indexes: bool = True) -> None:
        # do not actually delete Indexcard, just mark deleted:
        if self.deleted is None:
            self.deleted = timezone.now()
            self.save()
        (  # actually delete LatestResourceDescription:
            LatestResourceDescription.objects
            .filter(indexcard=self)
            .delete()
        )
        (  # actually delete DerivedIndexcard:
            DerivedIndexcard.objects
            .filter(upriver_indexcard=self)
            .delete()
        )
        if notify_indexes:
            # TODO: rearrange to avoid local import
            from share.search.index_messenger import IndexMessenger
            IndexMessenger().notify_indexcard_update([self])

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}({self.uuid}, {self.source_record_suid})'

    def __str__(self) -> str:
        return repr(self)

    @transaction.atomic
    def update_resource_description(
        self,
        focus_iri: str,
        rdf_tripledict: rdf.RdfTripleDictionary,
        expiration_date: datetime.date | None = None,
    ) -> ResourceDescription:
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
        _rdf_as_turtle, _turtle_checksum_iri = _turtlify(rdf_tripledict)
        _archived, _archived_created = ArchivedResourceDescription.objects.get_or_create(
            indexcard=self,
            turtle_checksum_iri=_turtle_checksum_iri,
            defaults={
                'rdf_as_turtle': _rdf_as_turtle,
                'focus_iri': focus_iri,
                'expiration_date': expiration_date,
            },
        )
        if (not _archived_created) and (_archived.rdf_as_turtle != _rdf_as_turtle):
            raise DigestiveError(f'hash collision? {_archived}\n===\n{_rdf_as_turtle}')
        if not self.deleted:
            _latest_resource_description, _created = LatestResourceDescription.objects.update_or_create(
                indexcard=self,
                defaults={
                    'turtle_checksum_iri': _turtle_checksum_iri,
                    'rdf_as_turtle': _rdf_as_turtle,
                    'focus_iri': focus_iri,
                    'expiration_date': expiration_date,
                },
            )
            return _latest_resource_description
        return _archived

    def update_supplementary_description(
        self,
        supplementary_suid: share_db.SourceUniqueIdentifier,
        focus_iri: str,
        rdf_tripledict: rdf.RdfTripleDictionary,
        expiration_date: datetime.date | None = None,
    ) -> SupplementaryResourceDescription:
        assert supplementary_suid.is_supplementary
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
        _rdf_as_turtle, _turtle_checksum_iri = _turtlify(rdf_tripledict)
        _supplement_rdf, _ = SupplementaryResourceDescription.objects.update_or_create(
            indexcard=self,
            supplementary_suid=supplementary_suid,
            defaults={
                'turtle_checksum_iri': _turtle_checksum_iri,
                'rdf_as_turtle': _rdf_as_turtle,
                'focus_iri': focus_iri,
                'expiration_date': expiration_date,
            },
        )
        return _supplement_rdf


###
# local helpers

def _turtlify(rdf_tripledict: rdf.RdfTripleDictionary) -> tuple[str, str]:
    '''return turtle serialization and checksum iri of that serialization'''
    _rdf_as_turtle = rdf.turtle_from_tripledict(rdf_tripledict)
    _turtle_checksum_iri = str(
        ChecksumIri.digest('sha-256', salt='', data=_rdf_as_turtle),
    )
    return (_rdf_as_turtle, _turtle_checksum_iri)
