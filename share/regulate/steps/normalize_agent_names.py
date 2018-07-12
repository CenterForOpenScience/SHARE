import re
import collections
import nameparser

from django.apps import apps

from share.models import AbstractAgent, Person
from share.regulate.steps import NodeStep
from share.transform.chain.links import GuessAgentTypeLink
from share.util import strip_whitespace


class NormalizeAgentNames(NodeStep):
    """Parse agent names and save in a normalized form.

    Example config:
    ```yaml
    - namespace: share.regulate.steps.node
      name: normalize_agent_names
    ```
    """
    NULL_RE = re.compile(r'^(?:\s*(none|null|empty)\s*)?$', re.I)
    NAME_PARTS = collections.OrderedDict([
        ('first', 'given_name'),
        ('middle', 'additional_name'),
        ('last', 'family_name'),
        ('suffix', 'suffix'),
    ])

    def valid_target(self, node):
        return node.model._meta.concrete_model is AbstractAgent

    def regulate_node(self, node):
        if issubclass(node.model, Person):
            self._normalize_person(node)
        else:
            self._normalize_non_person(node)

    def _normalize_person(self, node):
        attrs = node.attrs()
        name = max(
            ' '.join(filter(None, (
                attrs.get(x, '')
                for x in self.NAME_PARTS.values()
            ))),
            attrs.get('name', ''),
            key=len
        )

        if not name or self.NULL_RE.match(name):
            self.info('Discarding unnamed person', node.id)
            node.delete()
            return

        human = nameparser.HumanName(name)
        for part_name, field_name in self.NAME_PARTS.items():
            part = human[part_name]
            if part:
                node[field_name] = part.title()

        node['name'] = ' '.join(filter(None, (
            node[k] for k in self.NAME_PARTS.values()
        )))

    def _normalize_non_person(self, node):
        # TODO reevaluate everything in this method

        attrs = node.attrs()
        name = attrs.get('name')

        if not name or self.NULL_RE.match(name):
            self.info('Discarding unnamed agent', node.id)
            node.delete()
            return

        # Slightly more intelligent title casing
        name = re.sub(r'(?!for|and|the)\b[a-z]\w{2,}', lambda x: x.group().title(), name)

        maybe_type = GuessAgentTypeLink(default=node.type).execute(name)
        # If the new type is MORE specific, IE encompasses FEWER types, upgrade. Otherwise ignore
        if len(apps.get_model('share', maybe_type).get_types()) < len(node.model.get_types()):
            node.type = maybe_type

        match = re.match(r'^(.*(?:Departa?ment|Institute).+?);(?: (.+?); )?([^;]+)$', name, re.I)
        if match:
            *parts, location = [strip_whitespace(x) for x in match.groups() if x and strip_whitespace(x)]
            node['name'] = ' - '.join(reversed(parts))
            node['location'] = location
            return

        match = re.match(r'^(.+?), ([^,]+), ([^,]+)$', name, re.I)
        if match:
            name, *location = [strip_whitespace(x) for x in match.groups() if x and strip_whitespace(x)]
            node['name'] = name
            node['location'] = ', '.join(location)

        node['name'] = name
