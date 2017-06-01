import re
import logging

from django.db import models
from django.db import IntegrityError

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField
from share.models.fuzzycount import FuzzyCountManager
from share.util import strip_whitespace


__all__ = ('Tag', 'Subject', 'ThroughTags', 'ThroughSubjects')
logger = logging.getLogger('share.normalize')

# TODO Rename this file


class Tag(ShareObject):
    name = models.TextField(unique=True)

    @classmethod
    def normalize(cls, node, graph):
        tags = [
            strip_whitespace(part).lower()
            for part in re.split(',|;', node.attrs['name'])
            if strip_whitespace(part)
        ]

        if len(tags) == 1 and tags[0] == node.attrs['name']:
            return

        logger.debug('Normalized "%s" to %s', node.attrs['name'], tags)

        # ensure tags are always created in the same order
        tags = [graph.create(None, 'tag', {'name': tag}) for tag in sorted(tags)]

        for tag in tags:
            for edge in node.related('work_relations'):
                through = graph.create(None, 'throughtags', {})
                graph.relate(through, tag)
                graph.relate(through, edge.subject.related('creative_work').related)

        graph.remove(node)

    def __str__(self):
        return self.name

    class Disambiguation:
        all = ('name',)


class Taxonomy(models.Model):
    name = models.TextField(unique=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)


class SubjectManager(FuzzyCountManager):
    def get_by_natural_key(self, subject):
        return self.get(name=subject)


class Subject(ShareObject):
    name = models.TextField()
    is_deleted = models.BooleanField(default=False)
    uri = ShareURLField(unique=True, null=True)
    taxonomy = models.ForeignKey(Taxonomy, on_delete=models.CASCADE)
    parent = ShareForeignKey('Subject', null=True, related_name='children')
    central_synonym = ShareForeignKey('Subject', null=True, related_name='custom_synonyms')

    objects = SubjectManager()

    @classmethod
    def normalize(cls, node, graph):
        synonym = node.attrs.get('central_synonym')
        if synonym and synonym['@id'] == node['@id']:
            node.attrs.pop('central_synonym')

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    class Meta:
        unique_together = ('name', 'taxonomy')

    class Disambiguation:
        # Special disambiguation case, handled in GraphDisambiguator._instance_for_subject
        all = ('uri',)


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
