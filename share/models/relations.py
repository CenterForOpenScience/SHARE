from django.db import models
from django.contrib.postgres.fields import ArrayField

from mptt.models import MPTTModel, TreeForeignKey

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

__all__ = ('WorkRelation', 'EntityRelation', 'Contribution', 'Award', 'WorkRelationType', 'EntityRelationType')


class WorkRelation(ShareObject):
    from_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    to_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')
    relation_type = TreeForeignKey('WorkRelationType')

    class Meta:
        unique_together = ('from_work', 'to_work', 'relation_type')


class EntityRelation(ShareObject):
    from_entity = ShareForeignKey('AbstractEntity', related_name='outgoing_%(class)ss')
    to_entity = ShareForeignKey('AbstractEntity', related_name='incoming_%(class)ss')
    relation_type = TreeForeignKey('EntityRelationType')

    class Meta:
        unique_together = ('from_entity', 'to_entity', 'relation_type')


class RelationTypeManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(name=key)


class AbstractRelationType(MPTTModel):
    name = models.TextField(unique=True)
    uris = ArrayField(models.TextField(), editable=False, default=list)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True, editable=False)

    objects = RelationTypeManager()

    def natural_key(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return super(AbstractRelationType, self).__eq__(other)

    @staticmethod
    def natural_key_field():
        return 'name'

    class Meta:
        abstract = True


class EntityRelationType(AbstractRelationType):
    pass


class WorkRelationType(AbstractRelationType):
    pass
