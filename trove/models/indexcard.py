from django.db import models
from django.db import transaction
import gather

from share.models import RawDatum, SourceUniqueIdentifier  # TODO: break this dependency
from trove.models.persistent_iri import PersistentIri


class RdfIndexcardManager(models.Manager):
    @transaction.atomic
    def save_indexcard(
        self, *,
        from_raw_datum: RawDatum,
        focus_iri: str,
        tripledict: gather.RdfTripleDictionary,
    ):
        _focus_piris = PersistentIri.objects.save_equivalent_piris(tripledict, focus_iri)
        if not _focus_piris:
            raise ValueError('non-zero focus_piris required')
        _existing = self.filter(from_raw_datum=from_raw_datum, focus_piris__in=_focus_piris)
        _existing.delete()  # TODO: safety rails?
        return self.create(
            from_raw_datum=from_raw_datum,
            card_as_turtle=gather.leaf__turtle(tripledict),
            focus_piris=_focus_piris,
            focustype_piris=[
                PersistentIri.objects.save_for_iri(_iri)
                for _iri in tripledict[focus_iri].get(gather.RDF.type, ())
            ],
        )


class RdfIndexcard(models.Model):
    objects = RdfIndexcardManager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    card_as_turtle = models.TextField()  # TODO: max length? store by checksum?
    from_raw_datum = models.ForeignKey(
        RawDatum,
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
            SourceUniqueIdentifier.objects
            .filter(id__in=suid_ids)
            .annotate(latest_rawdatum_id=models.Subquery(
                RawDatum.objects
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

    from_rdf_indexcard = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE)
    format_piri = models.ForeignKey(PersistentIri, on_delete=models.PROTECT, related_name='+')
    formatted_card = models.TextField()  # TODO: store by checksum

    class Meta:
        unique_together = [
            ('from_rdf_indexcard', 'format_piri'),
        ]
