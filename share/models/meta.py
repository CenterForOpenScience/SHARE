from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField


__all__ = ('Tag', 'Subject', 'ThroughTags', 'ThroughSubjects', 'SubjectTaxonomy')

# TODO Rename this file


class CyclicalTaxonomyError(Exception):
    pass


class Tag(ShareObject):
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name

    class Disambiguation:
        all = ('name',)


class SubjectTaxonomy(models.Model):
    source = models.OneToOneField('Source')

    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return '<{} {}: {}>'.format(self.__class__.__name__, self.id, self.source.long_title)

    class Meta:
        verbose_name_plural = 'Subject Taxonomies'


class Subject(ShareObject):
    name = models.TextField()
    is_deleted = models.BooleanField(default=False)
    uri = ShareURLField(null=True, blank=True)
    taxonomy = models.ForeignKey(SubjectTaxonomy, editable=False, on_delete=models.CASCADE)
    parent = ShareForeignKey('Subject', blank=True, null=True, related_name='children')
    central_synonym = ShareForeignKey('Subject', blank=True, null=True, related_name='custom_synonyms')

    def save(self, *args, **kwargs):
        if self.id is not None and self.parent is not None:
            new_lineage = self.parent.lineage()
            if self in new_lineage:
                raise CyclicalTaxonomyError('Making {} a child of {} would cause a cycle!'.format(self, self.parent))
        return super().save(*args, **kwargs)

    def lineage(self):
        query = '''
            WITH RECURSIVE lineage_chain(id, parent, depth, path, cycle) AS (
                    SELECT id, parent_id, 1, ARRAY[id], false FROM {table} WHERE id = %(id)s
                  UNION
                    SELECT {table}.id, {table}.parent_id, lineage_chain.depth + 1, path || {table}.id, {table}.id = ANY(path)
                    FROM lineage_chain JOIN {table} ON lineage_chain.parent = {table}.id
                    WHERE NOT cycle
            )
            SELECT {table}.* FROM {table} INNER JOIN lineage_chain ON {table}.id = lineage_chain.id ORDER BY lineage_chain.depth DESC
        '''.format(table=self._meta.db_table)
        lineage = list(self._meta.model.objects.raw(query, params={'id': self.id}))
        if lineage[0].parent is not None:
            raise CyclicalTaxonomyError('Subject taxonomy cycle! {}'.format(lineage))
        return lineage

    def __str__(self):
        return self.name

    class Meta:
        unique_together = (('name', 'taxonomy'), ('uri', 'taxonomy'))

    class Disambiguation:
        all = ('name', 'central_synonym')


# Through Tables for all the things

class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag, related_name='work_relations')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='tag_relations')

    class Meta(ShareObject.Meta):
        unique_together = ('tag', 'creative_work')
        verbose_name_plural = 'through tags'

    class Disambiguation:
        all = ('tag', 'creative_work')


class ThroughSubjects(ShareObject):
    subject = ShareForeignKey('Subject', related_name='work_relations')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='subject_relations')
    is_deleted = models.BooleanField(default=False)

    class Meta(ShareObject.Meta):
        unique_together = ('subject', 'creative_work')
        verbose_name_plural = 'through subjects'

    class Disambiguation:
        all = ('subject', 'creative_work')
