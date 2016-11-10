import re
import logging

from django.db import models
from django.db import IntegrityError

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey
from share.util import strip_whitespace


__all__ = ('Tag', 'Subject')
logger = logging.getLogger('share.normalize')

# TODO Rename this file


class Tag(ShareObject):
    name = models.TextField(unique=True)

    disambiguation_fields = ('name',)

    @classmethod
    def normalize(cls, node, graph):
        tags = [
            strip_whitespace(part).lower()
            for part in re.split(',|;', node.attrs['name'])
            if strip_whitespace(part)
        ]

        logger.debug('Normalized %s to %s', node.attrs['name'], tags)

        nodes = [graph.create(attrs={'name': tag}) for tag in tags]

        graph.replace(node, *nodes)

    def __str__(self):
        return self.name


class SubjectManager(models.Manager):
    def get_by_natural_key(self, subject):
        return self.get(name=subject)


class Subject(models.Model):
    parent = models.ForeignKey('self', null=True)
    name = models.TextField(unique=True, db_index=True)

    objects = SubjectManager()

    disambiguation_fields = ('name',)

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    def save(self):
        raise IntegrityError('Subjects are an immutable set! Do it in bulk, if you must.')


# Through Tables for all the things

class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag)
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('tag', 'creative_work')


class ThroughSubjects(ShareObject):
    subject = models.ForeignKey('Subject')
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('subject', 'creative_work')
