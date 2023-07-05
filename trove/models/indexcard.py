from django.db import models
from django.db import transaction
import gather

from share import models as share_db  # TODO: break this dependency
from trove.exceptions import DigestiveError
from trove.models.persistent_iri import PersistentIri


class RdfIndexcardManager(models.Manager):
    @transaction.atomic
    def set_indexcards_for_raw_datum(
        self, *,
        from_raw_datum: share_db.RawDatum,
        tripledicts_by_focus_iri: dict[str, gather.RdfTripleDictionary],
    ):
        _prior_indexcards = self.filter(from_raw_datum=from_raw_datum)
        _prior_indexcards.delete()  # TODO: ponder provenance -- external updates will be in a new RawDatum, so this will only delete on re-ingestion... maybe fine?
        from_raw_datum.no_output = (not tripledicts_by_focus_iri)
        from_raw_datum.save(update_fields=['no_output'])
        _indexcards = []
        for _focus_iri, _tripledict in tripledicts_by_focus_iri.items():
            if _focus_iri not in _tripledict:
                raise DigestiveError(f'expected {_focus_iri} in {set(_tripledict.keys())}')
            _focus_piri_set = PersistentIri.objects.save_equivalent_piri_set(_tripledict, _focus_iri)
            _focustype_piri_set = [  # TODO: require non-zero?
                PersistentIri.objects.get_or_create_for_iri(_iri)
                for _iri in _tripledict[_focus_iri].get(gather.RDF.type, ())
            ]
            _indexcard = self.create(
                from_raw_datum=from_raw_datum,
                focus_iri=_focus_iri,
                card_as_turtle=gather.tripledict_as_turtle(_tripledict),
            )
            _indexcard.focus_piri_set.set(_focus_piri_set)
            _indexcard.focustype_piri_set.set(_focustype_piri_set)
            _indexcards.append(_indexcard)
        return _indexcards

    def latest_by_suid_ids(self, suid_ids, *, with_suid_id_annotation=False):
        _queryset = self.filter(
            from_raw_datum__in=share_db.RawDatum.objects.latest_by_suid_ids(suid_ids),
        )
        if with_suid_id_annotation:
            _queryset = _queryset.annotate(
                suid_id=models.F('from_raw_datum__suid_id'),
            )
        return _queryset


class RdfIndexcard(models.Model):
    objects = RdfIndexcardManager()

    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    from_raw_datum = models.ForeignKey(
        share_db.RawDatum,
        on_delete=models.CASCADE,
        related_name='rdf_indexcard_set',
    )
    focus_iri = models.TextField()  # exact iri used in card_as_turtle
    card_as_turtle = models.TextField()  # TODO: max length? store by checksum?

    # distant:
    focus_piri_set = models.ManyToManyField(PersistentIri, related_name='rdf_indexcard_set')
    focustype_piri_set = models.ManyToManyField(PersistentIri, related_name='+')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('from_raw_datum', 'focus_iri'),
                name='%(app_label)s_%(class)s_rawdatum_focusiri',
            ),
        ]

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


class DerivedIndexcard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    suid = models.ForeignKey(share_db.SourceUniqueIdentifier, on_delete=models.CASCADE, related_name='derived_indexcard_set')
    upriver_card = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE, related_name='derived_indexcard_set')
    deriver_piri = models.ForeignKey(PersistentIri, on_delete=models.PROTECT, related_name='+')
    card_as_text = models.TextField()  # TODO: store by checksum

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('suid', 'deriver_piri'),
                name='%(app_label)s_%(class)s_suid_deriverpiri',
            ),
        ]
