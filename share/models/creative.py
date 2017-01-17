from django.db import models
from django.utils.translation import ugettext_lazy as _

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.meta import Tag, Subject
from share.models.fields import ShareManyToManyField, ShareURLField

from share.util import strip_whitespace, ModelGenerator


# Base Creative Work class

class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField(blank=True, help_text='')
    description = models.TextField(blank=True, help_text='')
    is_deleted = models.BooleanField(default=False, help_text=_('Determines whether or not this record will be discoverable via search.'))
    date_published = models.DateTimeField(null=True)
    date_updated = models.DateTimeField(null=True)
    free_to_read_type = ShareURLField(blank=True)
    free_to_read_date = models.DateTimeField(null=True)
    rights = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True, help_text=_('The ISO 3166-1 alpha-2 country code indicating the language of this record.'))

    subjects = ShareManyToManyField(Subject, related_name='subjected_works', through='ThroughSubjects')
    tags = ShareManyToManyField(Tag, related_name='tagged_works', through='ThroughTags')

    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentWorkRelation')
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractWorkRelation', through_fields=('subject', 'related'), symmetrical=False)

    @classmethod
    def normalize(self, node, graph):
        for k, v in tuple(node.attrs.items()):
            if isinstance(v, str):
                node.attrs[k] = strip_whitespace(v)
                if node.attrs[k] == 'null':
                    node.attrs[k] = ''

    class Disambiguation:
        any = ('identifiers',)

    class Meta:
        db_table = 'share_creativework'

    def __str__(self):
        return self.title

generator = ModelGenerator(field_types={
    'text': models.TextField,
    'boolean': models.NullBooleanField,  # Has to be nullable for types models :(
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractCreativeWork))
