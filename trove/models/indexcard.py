from typing import Optional
import uuid

from django.db import models
from django.db import transaction
from django.utils import timezone
from gather import primitive_rdf

from share import models as share_db  # TODO: break this dependency
from share.search.index_messenger import IndexMessenger
from share.util.checksum_iri import ChecksumIri
from trove.exceptions import DigestiveError
from trove.models.resource_identifier import ResourceIdentifier
from trove.vocab.namespaces import RDF
from trove.vocab.trove import trove_indexcard_iri, trove_indexcard_namespace


class IndexcardManager(models.Manager):
    def get_for_iri(self, iri: str):
        _uuid = primitive_rdf.IriNamespace.without_namespace(iri, namespace=trove_indexcard_namespace())
        return self.get(uuid=_uuid)

    @transaction.atomic
    def save_indexcards_from_tripledicts(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledicts_by_focus_iri: dict[str, primitive_rdf.RdfTripleDictionary],
        undelete: bool = False,
    ) -> list['Indexcard']:
        from_raw_datum.no_output = (not rdf_tripledicts_by_focus_iri)
        from_raw_datum.save(update_fields=['no_output'])
        _indexcards = []
        _seen_focus_identifier_ids = set()
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
    def save_indexcard_from_tripledict(
        self, *,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledict: primitive_rdf.RdfTripleDictionary,
        focus_iri: str,
        undelete: bool = False,
    ):
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
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
        IndexcardRdf.save_indexcard_rdf(
            indexcard=_indexcard,
            from_raw_datum=from_raw_datum,
            rdf_tripledict=rdf_tripledict,
            focus_iri=focus_iri,
        )
        return _indexcard


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

    @property
    def latest_rdf(self) -> Optional['LatestIndexcardRdf']:
        '''convenience for the "other side" of LatestIndexcardRdf.indexcard
        '''
        return self.trove_latestindexcardrdf_set.first()

    @property
    def archived_rdf_set(self):
        '''convenience for the "other side" of ArchivedIndexcardRdf.indexcard

        returns a RelatedManager
        '''
        return self.trove_archivedindexcardrdf_set

    def get_iri(self):
        return trove_indexcard_iri(self.uuid)

    @transaction.atomic
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

    def as_rdf_tripledict(self) -> primitive_rdf.RdfTripleDictionary:
        return primitive_rdf.tripledict_from_turtle(self.rdf_as_turtle)

    class Meta:
        abstract = True

    def __repr__(self):
        return f'<{self.__class__.__qualname__}({self.id}, "{self.focus_iri}")'

    def __str__(self):
        return repr(self)

    @transaction.atomic
    @staticmethod
    def save_indexcard_rdf(
        indexcard: Indexcard,
        from_raw_datum: share_db.RawDatum,
        rdf_tripledict: primitive_rdf.RdfTripleDictionary,
        focus_iri: str,
    ) -> 'IndexcardRdf':
        if focus_iri not in rdf_tripledict:
            raise DigestiveError(f'expected {focus_iri} in {set(rdf_tripledict.keys())}')
        _rdf_as_turtle = primitive_rdf.tripledict_as_turtle(rdf_tripledict)
        _turtle_checksum_iri = str(
            ChecksumIri.digest('sha-256', salt='', raw_data=_rdf_as_turtle),
        )
        _archived, _archived_created = ArchivedIndexcardRdf.objects.get_or_create(
            indexcard=indexcard,
            from_raw_datum=from_raw_datum,
            turtle_checksum_iri=_turtle_checksum_iri,
            defaults={
                'rdf_as_turtle': _rdf_as_turtle,
                'focus_iri': focus_iri,
            },
        )
        if (not _archived_created) and (_archived.rdf_as_turtle != _rdf_as_turtle):
            raise DigestiveError(f'hash collision? {_archived}\n===\n{_rdf_as_turtle}')
        if not indexcard.deleted and from_raw_datum.is_latest():
            _latest_indexcard_rdf, _created = LatestIndexcardRdf.objects.update_or_create(
                indexcard=indexcard,
                defaults={
                    'from_raw_datum': from_raw_datum,
                    'turtle_checksum_iri': _turtle_checksum_iri,
                    'rdf_as_turtle': _rdf_as_turtle,
                    'focus_iri': focus_iri,
                },
            )
            return _latest_indexcard_rdf
        return _archived


class LatestIndexcardRdf(IndexcardRdf):
    # just the most recent version of this indexcard
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard',),
                name='%(app_label)s_%(class)s_uniq_indexcard',
            ),
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
