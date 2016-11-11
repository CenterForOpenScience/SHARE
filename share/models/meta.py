import re
import logging

from django.db import models
from django.db import IntegrityError

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey
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

        logger.debug('Normalized %s to %s', node.attrs['name'], tags)

        for tag in tags:
            tag = graph.create(None, 'tag', {'name': tag})
            for edge in node.related('work_relations'):
                through = graph.create(None, 'throughtags', {})
                graph.relate(through, tag)
                graph.relate(through, edge.subject.related('creative_work').related)

        graph.remove(node)

    def __str__(self):
        return self.name

    class Disambiguation:
        all = ('name',)


class SubjectManager(models.Manager):
    def get_by_natural_key(self, subject):
        return self.get(name=subject)


class Subject(models.Model):
    parent = models.ForeignKey('self', null=True)
    name = models.TextField(unique=True, db_index=True)

    objects = SubjectManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    def save(self):
        raise IntegrityError('Subjects are an immutable set! Do it in bulk, if you must.')

    class Disambiguation:
        all = ('name',)


# Through Tables for all the things

class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag, related_name='work_relations')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='tag_relations')

    class Meta:
        unique_together = ('tag', 'creative_work')

    class Disambiguation:
        all = ('tag', 'creative_work')


class ThroughSubjects(ShareObject):
    subject = models.ForeignKey('Subject', related_name='work_relations')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='subject_relations')

    class Meta:
        unique_together = ('subject', 'creative_work')

    class Disambiguation:
        all = ('subject', 'creative_work')
