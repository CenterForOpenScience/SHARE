import logging

from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.meta import Tag, Subject
from share.models.change import Change
from share.models.fields import ShareManyToManyField, ShareURLField

from share.util import ModelGenerator


logger = logging.getLogger(__name__)


# Base Creative Work class
class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField(blank=True, help_text='')
    description = models.TextField(blank=True, help_text='')
    is_deleted = models.BooleanField(default=False, help_text=_('Determines whether or not this record will be discoverable via search.'))
    date_published = models.DateTimeField(blank=True, null=True)
    date_updated = models.DateTimeField(blank=True, null=True)
    free_to_read_type = ShareURLField(blank=True)
    free_to_read_date = models.DateTimeField(blank=True, null=True)
    rights = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True, help_text=_('The ISO 3166-1 alpha-2 country code indicating the language of this record.'))

    subjects = ShareManyToManyField(Subject, related_name='subjected_works', through='ThroughSubjects')
    tags = ShareManyToManyField(Tag, related_name='tagged_works', through='ThroughTags')

    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentWorkRelation')
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractWorkRelation', through_fields=('subject', 'related'), symmetrical=False)

    class Disambiguation:
        any = ('identifiers',)

    class Meta(ShareObject.Meta):
        db_table = 'share_creativework'
        verbose_name_plural = 'Creative Works'

    def defrankenize(self, *_, im_really_sure_about_this=False):
        if not im_really_sure_about_this:
            raise ValueError('You have to be really sure about this')

        logger.info('Defrankenizing %r', self)

        with transaction.atomic():
            logger.info('Removing relations')
            for field in AbstractCreativeWork._meta.get_fields():
                if not field.one_to_many or field.name in ('changes', 'versions'):
                    continue

                logger.warning('Removing all %s', field.related_name)
                relation = getattr(self, field.get_accessor_name())
                num_deleted, stats = Change.objects.filter(id__in=relation.values_list('change_id', flat=True)).delete()
                logger.warning('Deleted %d changes to remove %s', num_deleted, field.related_name)

                assert num_deleted == stats.pop('share.Change', 0)

                if stats:
                    logger.error('Unexpectedly removed other rows, %r', stats)
                    raise ValueError('Unexpectedly removed other rows, {!r}'.format(stats))

            logger.info('Relations removed')
            self.administrative_change(is_deleted=True, title='Defrankenized work')

    def __str__(self):
        return self.title


generator = ModelGenerator(field_types={
    'text': models.TextField,
    'boolean': models.NullBooleanField,  # Has to be nullable for types models :(
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractCreativeWork))
