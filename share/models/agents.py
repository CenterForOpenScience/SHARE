import re
import logging
import nameparser
import collections

from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField
from share.normalize.links import GuessAgentTypeLink
from share.util import strip_whitespace, ModelGenerator


logger = logging.getLogger('share.normalize')
NULL_RE = re.compile(r'(^$)|(\s*(none|null|empty)\s*)', re.I)
NAME_PARTS = collections.OrderedDict([('first', 'given_name'), ('middle', 'additional_name'), ('last', 'family_name'), ('suffix', 'suffix')])

AGENT_RE = r'^(.*Departa?ment.+?); (.+?); ([^;]+)$'


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    """
    An Agent is a thing that has the power to act, to make decisions,
    to produce or contribute to the production of creative works.
    Either an individual person or a group of people.
    """

    name = models.TextField(blank=True)
    location = models.TextField(blank=True)
    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    @classmethod
    def normalize(cls, node, graph):
        name = strip_whitespace(node.attrs['name'])
        if NULL_RE.match(name):
            logger.debug('Discarding unnamed agent "%s"', node.attrs['name'])
            return graph.remove(node)

        node.type = GuessAgentTypeLink(default=node.type).execute(node.attrs['name'])

        match = re.match(r'^(.*(?:Departa?ment|Institute).+?);(?: (.+?); )?([^;]+)$', name, re.I)
        if match:
            *parts, location = [strip_whitespace(x) for x in match.groups() if x and strip_whitespace(x)]
            node.attrs['name'] = ' - '.join(reversed(parts))
            node.attrs['location'] = location
            return

        match = re.match(r'^(.+?), ([^,]+), ([^,]+)$', name, re.I)
        if match:
            name, *location = [strip_whitespace(x) for x in match.groups() if x and strip_whitespace(x)]
            node.attrs['name'] = name
            node.attrs['location'] = ', '.join(location)

        node.attrs['name'] = name
        if node.attrs.get('location'):
            node.attrs['location'] = strip_whitespace(node.attrs['location'])

    disambiguation_fields = ('identifiers',)

    class Meta:
        db_table = 'share_agent'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


generator = ModelGenerator(field_types={
    'text': models.TextField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgent))


def normalize_person(cls, node, graph):
    name = max(strip_whitespace(' '.join(
        node.attrs[x]
        for x in NAME_PARTS.values()
        if node.attrs.get(x)
    )), strip_whitespace(node.attrs.get('name', '')), '', key=len)

    if NULL_RE.match(name):
        logger.debug('Discarding unnamed agent "%s"', node.attrs['name'])
        return graph.remove(node)

    human = nameparser.HumanName(name)
    parts = {v: strip_whitespace(human[k]).title() for k, v in NAME_PARTS.items() if strip_whitespace(human[k])}

    node.attrs = {'name': ' '.join(parts[k] for k in NAME_PARTS.values() if k in parts), **parts}

    if node.attrs.get('location'):
        node.attrs['location'] = strip_whitespace(node.attrs['location'])

Person.normalize = classmethod(normalize_person)  # noqa
