from share.regulate.steps import NodeStep


class TrimCycles(NodeStep):
    """Remove circular relations

    Settings:
        relation_fields: Non-empty list of field names. If length 1, delete the node if the field
            points to itself. If length >1, delete the node if more than one of the given fields
            point to the same node.
        [delete_node]: Boolean (default True). If false, remove the offending edge(s) instead of
            deleting the node.
        [node_types]: Optional list of node types (inherited from NodeStep).
            If given, filter the list of nodes this step will consider.

    Example config:
    ```yaml
    - namespace: share.regulate.steps.node
      name: trim_cycles
      settings:
          relation_fields:
              - subject
              - related
          node_types:
              - agentrelation
    ```
    """
    def __init__(self, *args,
                 relation_fields,
                 delete_node=True,
                 **kwargs):
        super().__init__(*args, **kwargs)

        self.relation_fields = relation_fields
        self.delete_node = delete_node

    def regulate_node(self, node):
        if len(self.relation_fields) == 1:
            field_name = self.relation_fields[0]
            related = node[field_name]
            if related and related == node:
                self._trim(node)
        else:
            related_nodes = set(filter(
                node[f] for f in self.related_fields
            ))
            if len(related_nodes) != len(self.relation_fields):
                self._trim(node)

    def _trim(self, node):
        if self.delete_node:
            self.info('Discarding node with circular relation', node.id)
            node.delete()
        else:
            self.info('Discarding circular relations from node', node.id)
            for field_name in self.relation_fields:
                del node[field_name]
