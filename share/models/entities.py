from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField, ShareURLField

__all__ = ('Entity', 'Person', 'Organization', 'Institution')


class Entity(ShareObject, metaclass=TypedShareObjectMeta):
    name = models.TextField()
    location = models.TextField(blank=True)
    related_entities = ShareManyToManyField('Entity'

    class Meta:
        verbose_name_plural = 'Entities'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


class Person(Entity):
    family_name = models.TextField(blank=True, db_index=True)  # last
    given_name = models.TextField(blank=True, db_index=True)  # first
    additional_name = models.TextField(blank=True, db_index=True)  # can be used for middle
    suffix = models.TextField(blank=True, db_index=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return ' '.join(x for x in [self.given_name, self.family_name, self.additional_name, self.suffix] if x)

    class Meta:
        verbose_name_plural = 'People'
        index_together = (
            ('family_name', 'given_name', 'additional_name', 'suffix')
        )


class Organization(Entity):
    pass


class Institution(Entity):
    pass
