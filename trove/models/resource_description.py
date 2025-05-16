from __future__ import annotations
import datetime

from django.db import models
from primitive_metadata import primitive_rdf as rdf

__all__ = (
    'ArchivedResourceDescription',
    'ResourceDescription',
    'LatestResourceDescription',
    'SupplementaryResourceDescription',
)


class ResourceDescription(models.Model):
    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    indexcard = models.ForeignKey(
        'trove.Indexcard',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
    )
    turtle_checksum_iri = models.TextField(db_index=True)
    focus_iri = models.TextField()  # exact iri used in rdf_as_turtle
    rdf_as_turtle = models.TextField()  # TODO: store elsewhere by checksum

    # optional:
    expiration_date = models.DateField(
        null=True,
        blank=True,
        help_text='An (optional) date when this description will no longer be valid.',
    )

    class Meta:
        abstract = True

    @property
    def is_expired(self) -> bool:
        return (
            self.expiration_date is not None
            and self.expiration_date <= datetime.date.today()
        )

    def as_rdf_tripledict(self) -> rdf.RdfTripleDictionary:
        return rdf.tripledict_from_turtle(self.rdf_as_turtle)

    def as_quoted_graph(self) -> rdf.QuotedGraph:
        return rdf.QuotedGraph(
            self.as_rdf_tripledict(),
            focus_iri=self.focus_iri,
        )

    def as_rdfdoc_with_supplements(self) -> rdf.RdfGraph:
        '''build an rdf graph composed of this rdf and all current card supplements'''
        _rdfdoc = rdf.RdfGraph(self.as_rdf_tripledict())
        for _supplement in self.indexcard.supplementary_description_set.all():
            _rdfdoc.add_tripledict(_supplement.as_rdf_tripledict())
        return _rdfdoc

    def __repr__(self):
        return f'<{self.__class__.__qualname__}({self.id}, "{self.focus_iri}")'

    def __str__(self):
        return repr(self)


class LatestResourceDescription(ResourceDescription):
    # just the most recent version of this indexcard
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard',),
                name='trove_latestindexcardrdf_uniq_indexcard',
                # TODO when on django 5.2:
                # name='%(app_label)s_%(class)s_uniq_indexcard',
                # ...and add migration with `AlterConstraint` to rename
            ),
        ]
        indexes = [
            models.Index(
                fields=('modified',),  # for OAI-PMH selective harvest
                name='trove_lates_modifie_c6b0b1_idx',
                # TODO when on django 5.2:
                # remove explicit name, add migration with `RenameIndex` to match
            ),
            models.Index(fields=['expiration_date']),  # for expiring
        ]


class ArchivedResourceDescription(ResourceDescription):
    # all versions of an indexcard over time (including the latest)
    pass


class SupplementaryResourceDescription(ResourceDescription):
    # supplementary (non-descriptive) metadata from the same source (just the most recent)
    supplementary_suid = models.ForeignKey(
        'share.SourceUniqueIdentifier',
        on_delete=models.CASCADE,
        related_name='supplementary_description_set',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('indexcard', 'supplementary_suid'),
                name='trove_supplementaryindexcardrdf_uniq_supplement',
                # TODO when on django 5.2:
                # name='%(app_label)s_%(class)s_uniq_supplement',
                # ...and add migration with `AlterConstraint` to rename
            ),
        ]
        indexes = [
            models.Index(fields=['expiration_date']),  # for expiring
        ]
