import re

from share.regulate.steps import NodeStep
from share.util import strip_whitespace


class TokenizeTags(NodeStep):
    """Recognize lists of tags, split them into multiple nodes

    Example config:
    ```yaml
    - namespace: share.regulate.steps.node
      name: tokenize
    ```
    """
    node_types = ('tag',)

    def regulate_node(self, node):
        tags = list(map(
            lambda t: t.lower(),
            filter(None, (
                strip_whitespace(part)
                for part in re.split(',|;', node['name'])
            ))
        ))

        if not tags:
            self.info('Discarding nameless tag', node.id)
            node.delete()
            return

        if len(tags) == 1:
            node['name'] = tags[0]
            return

        through_tags = node['work_relations']
        for tag in sorted(tags):
            new_tag = node.graph.add_node(None, 'tag', name=tag)
            self.info('Added tokenized tag', new_tag.id)
            for through_tag in through_tags:
                node.graph.add_node(None, 'throughtags', tag=new_tag, creative_work=through_tag['creative_work'])

        self.info('Discarded tag with multiple names', node.id)
        node.delete()
