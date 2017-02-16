import re
import logging
import nameparser
import collections

from django.db import models
from django.apps import apps

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField
from share.transform.tools.links import GuessAgentTypeLink
from share.util import strip_whitespace, ModelGenerator


logger = logging.getLogger('share.normalize')
NULL_RE = re.compile(r'^(?:\s*(none|null|empty)\s*)?$', re.I)
NAME_PARTS = collections.OrderedDict([('first', 'given_name'), ('middle', 'additional_name'), ('last', 'family_name'), ('suffix', 'suffix')])

AGENT_RE = r'^(.*Departa?ment.+?); (.+?); ([^;]+)$'


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    """
    An Agent is an entity that has the power to act, e.g. an individual person or a group of people.

    Agents make decisions and produce or contribute to the production of creative works.
    """

    name = models.TextField(blank=True, db_index=True)
    location = models.TextField(blank=True)
    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    @classmethod
    def normalize(cls, node, graph):
        if 'name' not in node.attrs and not node.is_blank:
            return

        name = strip_whitespace(node.attrs['name'])

        # Slightly more intellegent title casing
        name = re.sub(r'(?!for|and|the)\b[a-z]\w{2,}', lambda x: x.group().title(), name)

        if NULL_RE.match(name):
            logger.debug('Discarding unnamed agent "%s"', name)
            return graph.remove(node)

        maybe_type = GuessAgentTypeLink(default=node.type).execute(node.attrs['name'])
        # If the new type is MORE specific, IE encompasses FEWER types, upgrade. Otherwise ignore
        if len(apps.get_model('share', maybe_type).get_types()) < len(node.model.get_types()):
            node._type = maybe_type

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

    class Disambiguation:
        any = ('identifiers', 'work_relations')
        constrain_types = True

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
    if node.attrs.get('location'):
        node.attrs['location'] = strip_whitespace(node.attrs['location'])

    if not node.is_blank and not ({'name', *NAME_PARTS.values()} & node.attrs.keys()):
        return

    name = max(strip_whitespace(' '.join(
        node.attrs[x]
        for x in NAME_PARTS.values()
        if node.attrs.get(x)
    )), strip_whitespace(node.attrs.get('name', '')), '', key=len)

    if NULL_RE.match(name):
        logger.debug('Discarding unnamed agent "%s"', node.attrs.get('name', ''))
        return graph.remove(node)

    human = nameparser.HumanName(name)
    parts = {v: strip_whitespace(human[k]).title() for k, v in NAME_PARTS.items() if strip_whitespace(human[k])}

    node.attrs = {'name': ' '.join(parts[k] for k in NAME_PARTS.values() if k in parts), **parts}

Person.normalize = classmethod(normalize_person)  # noqa


class UniqueNameDisambiguation(AbstractAgent.Disambiguation):
    any = AbstractAgent.Disambiguation.any + ('name',)

Institution.Disambiguation = UniqueNameDisambiguation # noqa
Organization.Disambiguation = UniqueNameDisambiguation # noqa
Consortium.Disambiguation = UniqueNameDisambiguation # noqa
Department.Disambiguation = AbstractAgent.Disambiguation # noqa
