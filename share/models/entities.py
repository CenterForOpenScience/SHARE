from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField

__all__ = ('AbstractEntity', 'Person', 'Organization', 'Institution')


class AbstractEntity(ShareObject, metaclass=TypedShareObjectMeta):
    name = models.TextField(blank=True)
    location = models.TextField(blank=True)
    related_entities = ShareManyToManyField('AbstractEntity', through='EntityRelation', through_fields=('from_entity', 'to_entity'), symmetrical=False)

    class Meta:
        verbose_name_plural = 'AbstractEntities'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


class Person(AbstractEntity):
    family_name = models.TextField(blank=True, db_index=True)  # last
    given_name = models.TextField(blank=True, db_index=True)  # first
    additional_name = models.TextField(blank=True, db_index=True)  # can be used for middle
    suffix = models.TextField(blank=True, db_index=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return ' '.join(x for x in [self.given_name, self.family_name, self.additional_name, self.suffix] if x)

    def save(self, *args, **kwargs):
        # TODO better way of reconciling Entity.name with Person.{family,given,additional}_name?
        if not self.name:
            self.name = self.get_full_name()
        super(Person, self).save(*args, **kwargs)

# TODO if Person.Meta is defined, system check complains "(models.E017) Proxy model 'Person' contains model fields."
#    class Meta:
#        verbose_name_plural = 'People'
#        index_together = (
#            ('family_name', 'given_name', 'additional_name', 'suffix')
#        )


class Organization(AbstractEntity):
    pass


class Institution(AbstractEntity):
    pass
