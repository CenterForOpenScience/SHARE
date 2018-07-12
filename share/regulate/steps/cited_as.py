from share.regulate.steps import NodeStep


class CitedAs(NodeStep):
    """Set contributor cited_as, if empty.

    Example config:
    ```yaml
    - namespace: share.regulate.steps.node
      name: cited_as
    ```
    """
    node_types = ['abstractagentworkrelation']

    def regulate_node(self, node):
        if not node['cited_as']:
            node['cited_as'] = node['agent']['name']
