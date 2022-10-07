from share.legacy_normalize.regulate.steps import NodeStep


class BlockExtraValues(NodeStep):
    """Discard nodes based on key/value pairs in their `extra` dict

    Settings:
        blocked_values: Non-empty dict. If all its key/value pairs exist in a
            node's `extra`, discard that node.
        [node_types]: Optional list of node types (inherited from NodeStep).
            If given, filter the list of nodes this step will consider.

    Example config (YAML):
        Discard work identifiers with {'identifier_type': 'srbnumber'}

        ```yaml
        - namespace: share.regulate.steps.node
          name: block_extra_values
          settings:
            node_types:
              - WorkIdentifer
            blocked_values:
              identifier_type: srbnumber
        ```
    """
    def __init__(self, *args, blocked_values, **kwargs):
        super().__init__(*args, **kwargs)
        if not blocked_values or not isinstance(blocked_values, dict):
            raise TypeError('blocked_values setting must be a non-empty dict')
        self.blocked_values = blocked_values

    def regulate_node(self, node):
        extra = node['extra']
        if not extra:
            return

        if all(extra.get(k) == v for k, v in self.blocked_values.items()):
            node.delete()
            self.info(
                '{}: Extra data match blocked values {}; deleting node.'.format(
                    self.__class__.__name__,
                    self.blocked_values
                ),
                node_id=node.id
            )
