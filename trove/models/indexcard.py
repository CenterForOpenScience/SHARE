from django.db import models
from django.db.models.functions import Coalesce
from django.db import transaction
import gather

from share import models as share_db  # TODO: break this dependency
from trove.exceptions import DigestiveError
from trove.models.resource_identifier import ResourceIdentifier


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
            _focus_identifier_set = ResourceIdentifier.objects.save_equivalent_identifier_set(_tripledict, _focus_iri)
            _focustype_identifier_set = [  # TODO: require non-zero?
                ResourceIdentifier.objects.get_or_create_for_iri(_iri)
                for _iri in _tripledict[_focus_iri].get(gather.RDF.type, ())
            ]
            _indexcard = self.create(
                from_raw_datum=from_raw_datum,
                focus_iri=_focus_iri,
                rdf_as_turtle=gather.tripledict_as_turtle(_tripledict),
            )
            _indexcard.focus_identifier_set.set(_focus_identifier_set)
            _indexcard.focustype_identifier_set.set(_focustype_identifier_set)
            _indexcards.append(_indexcard)
        return _indexcards


class IndexcardIdentifier(models.Model):
    objects = RdfIndexcardManager()

    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    suid = models.ForeignKey(
        share_db.SourceUniqueIdentifier,
        on_delete=models.CASCADE,
        related_name='indexcard_identifier_set',
    )
    resource_identifier = models.ForeignKey(
        ResourceIdentifier,
        on_delete=models.CASCADE,
        related_name='indexcard_identifier_set',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('suid', 'resource_identifier'),
                name='%(app_label)s_%(class)s_suid_focusidentifier',
            ),
        ]


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
    indexcard_identifier = models.ForeignKey(
        IndexcardIdentifier,
        on_delete=models.CASCADE,
        related_name='rdf_indexcard_set',
    )
    focus_iri = models.TextField()  # exact iri used in rdf_as_turtle
    rdf_as_turtle = models.TextField()  # TODO: store elsewhere by checksum

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard_identifier', 'from_raw_datum'),
                name='%(app_label)s_%(class)s_uniq_indexcardid_rawdatum',
            ),
        ]

    def as_rdf_tripledict(self) -> gather.RdfTripleDictionary:
        return gather.tripledict_from_turtle(self.rdf_as_turtle)

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

    upriver_card = models.ForeignKey(RdfIndexcard, on_delete=models.CASCADE, related_name='derived_indexcard_set')
    deriver_identifier = models.ForeignKey(ResourceIdentifier, on_delete=models.PROTECT, related_name='+')
    card_as_text = models.TextField()  # TODO: store elsewhere by checksum

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('upriver_card', 'deriver_identifier'),
                name='%(app_label)s_%(class)s_uprivercard_deriveridentifier',
            ),
        ]
