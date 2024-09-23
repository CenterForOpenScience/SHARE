from __future__ import annotations
import uuid

from django.db import models
from django.db import transaction
from django.utils import timezone
from primitive_metadata import primitive_rdf as rdf

from share import models as share_db  # TODO: break this dependency
from share.search.index_messenger import IndexMessenger
from share.util.checksum_iri import ChecksumIri
from trove.exceptions import DigestiveError
from trove.models.resource_identifier import ResourceIdentifier
from trove.vocab.namespaces import RDF
from trove.vocab.trove import trove_indexcard_iri, trove_indexcard_namespace


class IndexcardManager(models.Manager):
    def get_for_iri(self, iri: str):
        _uuid = rdf.iri_minus_namespace(iri, namespace=trove_indexcard_namespace())
        return self.get(uuid=_uuid)

    @transaction.atomic
    def save_indexcards_from_tripledicts(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledicts_by_focus_iri: dict[str, rdf.RdfTripleDictionary],
        undelete: bool = False,
    ) -> list['Indexcard']:
        assert not from_raw_datum.suid.is_supplementary
        from_raw_datum.no_output = (not rdf_tripledicts_by_focus_iri)
        from_raw_datum.save(update_fields=['no_output'])
        _indexcards = []
        _seen_focus_identifier_ids: set[str] = set()
        for _focus_iri, _tripledict in rdf_tripledicts_by_focus_iri.items():
            _indexcard = self.save_indexcard_from_tripledict(
                from_raw_datum=from_raw_datum,
                rdf_tripledict=_tripledict,
                focus_iri=_focus_iri,
                undelete=undelete,
            )
            _focus_identifier_ids = {_fid.id for _fid in _indexcard.focus_identifier_set.all()}
            if not _seen_focus_identifier_ids.isdisjoint(_focus_identifier_ids):
                _duplicates = (
                    ResourceIdentifier.objects
                    .filter(id__in=_seen_focus_identifier_ids.intersection(_focus_identifier_ids))
                )
                raise DigestiveError(f'duplicate focus iris: {list(_duplicates)}')
            _indexcards.append(_indexcard)
        # cards seen previously on this suid (but not this time) treated as deleted
        for _indexcard_to_delete in (
            Indexcard.objects
            .filter(source_record_suid=from_raw_datum.suid)
            .exclude(id__in=[_card.id for _card in _indexcards])
        ):
            _indexcard_to_delete.pls_delete()
        return _indexcards

    @transaction.atomic
    def supplement_indexcards_from_tripledicts(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledicts_by_focus_iri: dict[str, rdf.RdfTripleDictionary],
    ) -> list[Indexcard]:
        assert from_raw_datum.suid.is_supplementary
        from_raw_datum.no_output = (not rdf_tripledicts_by_focus_iri)
        from_raw_datum.save(update_fields=['no_output'])
        if not from_raw_datum.is_latest():
            return []
        _indexcards = []
        for _focus_iri, _tripledict in rdf_tripledicts_by_focus_iri.items():
            _indexcards.extend(self.supplement_indexcards(
                from_raw_datum=from_raw_datum,
                rdf_tripledict=_tripledict,
                focus_iri=_focus_iri,
            ))
        _seen_indexcard_ids = {_card.id for _card in _indexcards}
        # supplementary data seen previously on this suid (but not this time) should be deleted
        for _supplement_to_delete in (
            SupplementaryIndexcardRdf.objects
            .filter(supplementary_suid=from_raw_datum.suid)
            .exclude(from_raw_datum=from_raw_datum)
        ):
            if _supplement_to_delete.indexcard_id not in _seen_indexcard_ids:
                _indexcards.append(_supplement_to_delete.indexcard)
            _supplement_to_delete.delete()
        return _indexcards

    @transaction.atomic
    def save_indexcard_from_tripledict(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledict: rdf.RdfTripleDictionary,
        focus_iri: str,
        undelete: bool = False,
    ):
        assert not from_raw_datum.suid.is_supplementary
        _focus_identifier_set = (
            ResourceIdentifier.objects
            .save_equivalent_identifier_set(rdf_tripledict, focus_iri)
        )
        _focustype_identifier_set = [  # TODO: require non-zero?
            ResourceIdentifier.objects.get_or_create_for_iri(_iri)
            for _iri in rdf_tripledict[focus_iri].get(RDF.type, ())
        ]
        _indexcard = Indexcard.objects.filter(
            source_record_suid=from_raw_datum.suid,
            focus_identifier_set__in=_focus_identifier_set,
        ).first()
        if _indexcard is None:
            _indexcard = Indexcard.objects.create(source_record_suid=from_raw_datum.suid)
        if undelete and _indexcard.deleted:
            _indexcard.deleted = None
            _indexcard.save()
        _indexcard.focus_identifier_set.set(_focus_identifier_set)
        _indexcard.focustype_identifier_set.set(_focustype_identifier_set)
        _indexcard.update_rdf(
            from_raw_datum=from_raw_datum,
            rdf_tripledict=rdf_tripledict,
            focus_iri=focus_iri,
        )
        return _indexcard

    @transaction.atomic
    def supplement_indexcards(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledict: rdf.RdfTripleDictionary,
        focus_iri: str,
    ) -> list[Indexcard]:
        assert from_raw_datum.suid.is_supplementary
        # supplement indexcards with the same focus from the same source_config
        # (if none exist, fine, nothing gets supplemented)
        _indexcards = list(Indexcard.objects.filter(
            source_record_suid__source_config_id=from_raw_datum.suid.source_config_id,
            focus_identifier_set__in=ResourceIdentifier.objects.queryset_for_iri(focus_iri),
        ))
        for _indexcard in _indexcards:
            _indexcard.update_supplementary_rdf(
                from_raw_datum=from_raw_datum,
                rdf_tripledict=rdf_tripledict,
                focus_iri=focus_iri,
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
    def latest_rdf(self) -> LatestIndexcardRdf:
        '''convenience for the "other side" of LatestIndexcardRdf.indexcard
        '''
        return self.trove_latestindexcardrdf_set.get()  # may raise DoesNotExist

    @property
    def archived_rdf_set(self):
        '''convenience for the "other side" of ArchivedIndexcardRdf.indexcard

        returns a RelatedManager
        '''
        return self.trove_archivedindexcardrdf_set

    @property
    def supplementary_rdf_set(self):
        '''convenience for the "other side" of SupplementaryIndexcardRdf.indexcard

        returns a RelatedManager
        '''
        return self.trove_supplementaryindexcardrdf_set

    def get_iri(self):
        return trove_indexcard_iri(self.uuid)

    def pls_delete(self):
        # do not actually delete Indexcard, just mark deleted:
        if self.deleted is None:
            self.deleted = timezone.now()
            self.save()
        (  # actually delete LatestIndexcardRdf:
            LatestIndexcardRdf.objects
            .filter(indexcard=self)
            .delete()
        )
        (  # actually delete DerivedIndexcard:
            DerivedIndexcard.objects
            .filter(upriver_indexcard=self)
            .delete()
        )
        IndexMessenger().notify_indexcard_update([self])

    def __repr__(self):
        return f'<{self.__class__.__qualname__}({self.uuid}, {self.source_record_suid})'

    def __str__(self):
        return repr(self)

    @transaction.atomic
    def update_rdf(
        self,
        from_raw_datum: share_db.RawDatum,
        focus_iri: str,
        rdf_tripledict: rdf.RdfTripleDictionary,
    ) -> 'IndexcardRdf':
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
        _rdf_as_turtle, _turtle_checksum_iri = _turtlify(rdf_tripledict)
        _archived, _archived_created = ArchivedIndexcardRdf.objects.get_or_create(
            indexcard=self,
            from_raw_datum=from_raw_datum,
            turtle_checksum_iri=_turtle_checksum_iri,
            defaults={
                'rdf_as_turtle': _rdf_as_turtle,
                'focus_iri': focus_iri,
            },
        )
        if (not _archived_created) and (_archived.rdf_as_turtle != _rdf_as_turtle):
            raise DigestiveError(f'hash collision? {_archived}\n===\n{_rdf_as_turtle}')
        if not self.deleted and from_raw_datum.is_latest():
            _latest_indexcard_rdf, _created = LatestIndexcardRdf.objects.update_or_create(
                indexcard=self,
                defaults={
                    'from_raw_datum': from_raw_datum,
                    'turtle_checksum_iri': _turtle_checksum_iri,
                    'rdf_as_turtle': _rdf_as_turtle,
                    'focus_iri': focus_iri,
                },
            )
            return _latest_indexcard_rdf
        return _archived

    def update_supplementary_rdf(
        self,
        from_raw_datum: share_db.RawDatum,
        focus_iri: str,
        rdf_tripledict: rdf.RdfTripleDictionary,
    ) -> SupplementaryIndexcardRdf:
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
        _rdf_as_turtle, _turtle_checksum_iri = _turtlify(rdf_tripledict)
        _supplement_rdf, _ = SupplementaryIndexcardRdf.objects.update_or_create(
            indexcard=self,
            supplementary_suid=from_raw_datum.suid,
            defaults={
                'from_raw_datum': from_raw_datum,
                'turtle_checksum_iri': _turtle_checksum_iri,
                'rdf_as_turtle': _rdf_as_turtle,
                'focus_iri': focus_iri,
            },
        )
        return _supplement_rdf


class IndexcardRdf(models.Model):
    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    from_raw_datum = models.ForeignKey(
        share_db.RawDatum,
        on_delete=models.CASCADE,
        related_name='+',
    )
    indexcard = models.ForeignKey(
        Indexcard,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
    )
    turtle_checksum_iri = models.TextField(db_index=True)
    focus_iri = models.TextField()  # exact iri used in rdf_as_turtle
    rdf_as_turtle = models.TextField()  # TODO: store elsewhere by checksum

    def as_rdf_tripledict(self) -> rdf.RdfTripleDictionary:
        return rdf.tripledict_from_turtle(self.rdf_as_turtle)

    def as_quoted_graph(self) -> rdf.QuotedGraph:
        return rdf.QuotedGraph(
            self.as_rdf_tripledict(),
            focus_iri=self.focus_iri,
        )

    class Meta:
        abstract = True

    def __repr__(self):
        return f'<{self.__class__.__qualname__}({self.id}, "{self.focus_iri}")'

    def __str__(self):
        return repr(self)


class LatestIndexcardRdf(IndexcardRdf):
    # just the most recent version of this indexcard
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard',),
                name='%(app_label)s_%(class)s_uniq_indexcard',
            ),
        ]
        indexes = [
            models.Index(fields=('modified',)),  # for OAI-PMH selective harvest
        ]


class ArchivedIndexcardRdf(IndexcardRdf):
    # all versions of an indexcard over time (including the latest)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard', 'from_raw_datum', 'turtle_checksum_iri'),
                name='%(app_label)s_%(class)s_uniq_archived_version',
            ),
        ]


class SupplementaryIndexcardRdf(IndexcardRdf):
    # supplementary (non-descriptive) metadata from the same source (just the most recent)
    supplementary_suid = models.ForeignKey(
        share_db.SourceUniqueIdentifier,
        on_delete=models.CASCADE,
        related_name='supplementary_rdf_set',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard', 'supplementary_suid'),
                name='%(app_label)s_%(class)s_uniq_supplement',
            ),
        ]


class DerivedIndexcard(models.Model):
    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    upriver_indexcard = models.ForeignKey(
        Indexcard,
        on_delete=models.CASCADE,
        related_name='derived_indexcard_set',
    )
    deriver_identifier = models.ForeignKey(ResourceIdentifier, on_delete=models.PROTECT, related_name='+')
    derived_checksum_iri = models.TextField()
    derived_text = models.TextField()  # TODO: store elsewhere by checksum

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('upriver_indexcard', 'deriver_identifier'),
                name='%(app_label)s_%(class)s_upriverindexcard_deriveridentifier',
            ),
        ]

    def __repr__(self):
        return f'<{self.__class__.__qualname__}({self.id}, {self.upriver_indexcard.uuid}, "{self.deriver_identifier.sufficiently_unique_iri}")'

    def __str__(self):
        return repr(self)

    @property
    def deriver_cls(self):
        from trove.derive import get_deriver_classes
        (_deriver_cls,) = get_deriver_classes(self.deriver_identifier.raw_iri_list)
        return _deriver_cls

    def as_rdf_literal(self) -> rdf.Literal:
        return rdf.literal(
            self.derived_text,
            datatype_iris=self.deriver_cls.derived_datatype_iris(),
        )


###
# local helpers

def _turtlify(rdf_tripledict: rdf.RdfTripleDictionary) -> tuple[str, str]:
    '''return turtle serialization and checksum iri of that serialization'''
    _rdf_as_turtle = rdf.turtle_from_tripledict(rdf_tripledict)
    _turtle_checksum_iri = str(
        ChecksumIri.digest('sha-256', salt='', raw_data=_rdf_as_turtle),
    )
    return (_rdf_as_turtle, _turtle_checksum_iri)
