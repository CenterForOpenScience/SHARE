import re

from share.legacy_normalize.regulate.steps import NodeStep
from share.legacy_normalize.transform.chain.links import GuessAgentTypeLink
from share.legacy_normalize.schema import ShareV2Schema
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

    def valid_target(self, node):
        return node.concrete_type == 'abstractagent'

    def regulate_node(self, node):
        if node.type == 'person':
            self._normalize_person(node)
        else:
            self._normalize_non_person(node)

    def _normalize_person(self, node):
        name = strip_whitespace(node['name'] or '')

        if not name:
            # try building the name from parts
            name = strip_whitespace(' '.join((
                node['given_name'] or '',
                node['additional_name'] or '',
                node['family_name'] or '',
                node['suffix'] or '',
            )))

        if not name:
            # try getting the name from "cited_as"
            cited_as_names = [
                relation['cited_as']
                for relation in node['work_relations']
                if relation['cited_as']
            ]
            if len(cited_as_names) == 1:
                name = cited_as_names[0]

        if not name or self.NULL_RE.match(name):
            self.info('Discarding unnamed person', node.id)
            node.delete()
        else:
            node['name'] = name

    def _normalize_non_person(self, node):
        name = node['name']
        if not name or self.NULL_RE.match(name):
            self.info('Discarding unnamed agent', node.id)
            node.delete()
            return

        maybe_type_name = GuessAgentTypeLink(default=node.type).execute(name)
        maybe_type = ShareV2Schema().get_type(maybe_type_name)
        # If the new type is MORE specific, upgrade. Otherwise ignore
        if maybe_type.distance_from_concrete_type > node.schema_type.distance_from_concrete_type:
            node.type = maybe_type.name

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
