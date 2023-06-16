from django.db import models
from django.db import transaction
import gather

from share.models.ingest import RawDatum
from share.models.persistent_iri import PersistentIri


class RdfIndexcardManager(models.Manager):
    @transaction.atomic
    def save_indexcard(
        self, *,
        from_raw_datum: RawDatum,
        focus_iri: str,
        tripledict: gather.RdfTripleDictionary,
    ):
        _focus_piris = (
            PersistentIri.objects
            .save_equivalent_piris(tripledict, focus_iri)
        )
        if not _focus_piris:
            raise ValueError('non-zero focus_piris required')
        _existing = self.filter(from_raw_datum=from_raw_datum, focus_piris__in=_focus_piris)
        _existing.delete()  # TODO: safety rails?
        return self.create(
            from_raw_datum=from_raw_datum,
            card_as_turtle=gather.leaf__turtle(tripledict),
            focus_piris=PersistentIri.objects.save_equivalent_piris(tripledict, focus_iri),
            focustype_piris=PersistentIri.objects.save_multiple_from_str(
                tripledict[focus_iri].get(gather.OWL.sameAs, ()),
            ),
        )


class RdfIndexcard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    from_raw_datum = models.ForeignKey(RawDatum, on_delete=models.CASCADE, related_name='rdf_indexcard_set')
    focus_piris = models.ManyToManyField(PersistentIri, related_name='+', through='ThruRdfIndexcardFocusPiris')
    focustype_piris = models.ManyToManyField(PersistentIri, related_name='+')
    card_as_turtle = models.TextField()  # TODO: max length?
    # TODO: card_as_turtle_checksum_iri

    def as_rdf_tripledict(self) -> gather.RdfTripleDictionary:
        return gather.tripledict_from_turtle(self.card_as_turtle)


# an explicit thru-table for RdfIndexcard.focus_iris, to allow additional constraint
class ThruRdfIndexcardFocusPiris(models.Model):
    rdf_indexcard = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE)
    persistent_iri = models.ForeignKey(PersistentIri, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            # no focus_iri duplicates allowed within an index card...
            models.UniqueConstraint('rdf_indexcard', 'persistent_iri'),
            # ...or across index cards extracted from the same raw datum
            models.UniqueConstraint('rdf_indexcard__from_raw_datum', 'persistent_iri'),
        ]


class DerivedIndexcard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    from_full_indexcard = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE)
    format_piri = models.ForeignKey(PersistentIri, related_name='+')
    formatted_card = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint('from_rdf_indexcard', 'format_piri'),
        ]
