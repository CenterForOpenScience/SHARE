from share.regulate.steps import NodeStep


class BlockExtraValues(NodeStep):
    def __init__(self, *args, blocked_values, **kwargs):
        super().__init__(*args, **kwargs)
        assert blocked_values and isinstance(blocked_values, dict), 'blocked_values option must be a non-empty dict'
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
