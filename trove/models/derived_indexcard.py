from __future__ import annotations
from typing import TYPE_CHECKING

from django.db import models
from primitive_metadata import primitive_rdf as rdf

from trove.models.resource_identifier import ResourceIdentifier
if TYPE_CHECKING:
    from trove.derive._base import IndexcardDeriver

__all__ = ('DerivedIndexcard',)


class DerivedIndexcard(models.Model):
    # auto:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # required:
    upriver_indexcard = models.ForeignKey(
        'trove.Indexcard',
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

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}({self.pk}, {self.upriver_indexcard.uuid}, "{self.deriver_identifier.sufficiently_unique_iri}")'

    def __str__(self) -> str:
        return repr(self)

    @property
    def deriver_cls(self) -> type[IndexcardDeriver]:
        from trove.derive import get_deriver_classes
        (_deriver_cls,) = get_deriver_classes(self.deriver_identifier.raw_iri_list)
        return _deriver_cls

    def as_rdf_literal(self) -> rdf.Literal:
        return rdf.literal(
            self.derived_text,
            datatype_iris=self.deriver_cls.derived_datatype_iris(),
        )
