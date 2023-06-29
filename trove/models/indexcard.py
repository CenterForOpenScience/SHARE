from django.db import models
from django.db import transaction
import gather

from share import models as share_db  # TODO: break this dependency
from trove.models.persistent_iri import PersistentIri


class RdfIndexcardManager(models.Manager):
    @transaction.atomic
    def save_indexcards_for_raw_datum(
        self, *,
        from_raw_datum: share_db.RawDatum,
        tripledicts_by_focus_iri: dict[str, gather.RdfTripleDictionary],
    ):
        _existing = self.filter(from_raw_datum=from_raw_datum)
        _existing.delete()  # TODO: ponder provenance -- external updates will be in a new RawDatum, so this will only delete on re-ingestion... maybe fine?
        _indexcards = []
        for _focus_iri, _tripledict in tripledicts_by_focus_iri.items():
            assert _focus_iri in _tripledict, f'expected {_focus_iri} in {set(_tripledict.keys())}'
            _focus_piris = PersistentIri.objects.save_equivalent_piris(_tripledict, _focus_iri)
            _focustype_piris = [  # TODO: require non-zero?
                PersistentIri.objects.get_or_create_for_iri(_iri)
                for _iri in _tripledict[_focus_iri].get(gather.RDF.type, ())
            ]
            _indexcard = self.create(
                from_raw_datum=from_raw_datum,
                focus_iri=_focus_iri,
                card_as_turtle=gather.tripledict_as_turtle(_tripledict),
            )
            _indexcard.focus_piris.set(_focus_piris)
            _indexcard.focustype_piris.set(_focustype_piris)
            _indexcards.append(_indexcard)
        return _indexcards


class RdfIndexcard(models.Model):
    objects = RdfIndexcardManager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    card_as_turtle = models.TextField()  # TODO: max length? store by checksum?
    focus_iri = models.TextField()
    from_raw_datum = models.ForeignKey(
        share_db.RawDatum,
        on_delete=models.CASCADE,
        related_name='rdf_indexcard_set',
    )
    focus_piris = models.ManyToManyField(
        PersistentIri,
        through='ThruRdfIndexcardFocusPiris',
        related_name='+',
    )
    focustype_piris = models.ManyToManyField(
        PersistentIri,
        related_name='+',
    )

    def as_rdf_tripledict(self) -> gather.RdfTripleDictionary:
        return gather.tripledict_from_turtle(self.card_as_turtle)

    def get_suid(self) -> share_db.SourceUniqueIdentifier:
        '''convenience to get self.from_raw_datum.suid without fetching the raw datum
        '''
        # database constraints (should) guarantee exactly one
        return share_db.SourceUniqueIdentifier.objects.get(raw_data__rdf_indexcard_set=self)

    def get_backcompat_sharev2_suid(self) -> share_db.SourceUniqueIdentifier:
        _suid = self.get_suid()
        # may raise SourceUniqueIdentifier.DoesNotExist
        return share_db.SourceUniqueIdentifier.objects.get(
            source_config__in=share_db.SourceConfig.objects.filter(
                source_id=_suid.source_config.source_id,
                transformer_key='v2_push',
            ),
            identifier=_suid.identifier,
        )


# an explicit thru-table for RdfIndexcard.focus_piris, to allow additional constraint
class ThruRdfIndexcardFocusPiris(models.Model):
    rdf_indexcard = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE)
    focus_piri = models.ForeignKey(PersistentIri, on_delete=models.CASCADE)

    class Meta:
        unique_together = [
            # no focus_piri duplicates allowed within an index card...
            ('rdf_indexcard', 'focus_piri'),
        ]
        # ...or across index cards extracted from the same raw datum (TODO sql or django4 CheckConstraint)
        # constraints = [
        #     models.UniqueConstraint('rdf_indexcard__from_raw_datum', 'focus_piri'),
        # ]


class DerivedIndexcardManager(models.Manager):
    def latest_by_suid_ids(self, suid_ids, *, with_suid_id_annotation=False):
        _suid_qs = (
            share_db.SourceUniqueIdentifier.objects
            .filter(id__in=suid_ids)
            .annotate(latest_rawdatum_id=models.Subquery(
                share_db.RawDatum.objects
                .filter(suid_id=models.OuterRef('id'))
                .order_by(models.Coalesce('datestamp', 'date_created').desc(nulls_last=True))
                .values('id')
                [:1]
            ))
        )
        _queryset = self.filter(
            from_rdf_indexcard__from_raw_datum_id__in=_suid_qs.values('latest_rawdatum_id'),
        )
        if with_suid_id_annotation:
            _queryset = _queryset.annotate(
                suid_id=models.F('from_rdf_indexcard__from_raw_datum__suid_id'),
            )
        return _queryset


class DerivedIndexcard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    upriver_card = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE)
    deriver_piri = models.ForeignKey(PersistentIri, on_delete=models.PROTECT, related_name='+')
    card_as_text = models.TextField()  # TODO: store by checksum

    class Meta:
        unique_together = [
            ('upriver_card', 'deriver_piri'),
        ]
