import re

from share.regulate.steps import NodeStep
from share.util import strip_whitespace


class StripWhitespace(NodeStep):
    """Normalize whitespace in string values.

    Strip leading and trailing whitespace, and replace non-space whitespace and
    multiple whitespace characters in a row with a single space.

    If a field value is an empty string or something like "none", discard it.

    Example config:
    ```yaml
    - namespace: share.regulate.steps.node
      name: whitespace
    ```
    """
    NULL_RE = re.compile(r'^(?:\s*(none|null|empty)\s*)?$', re.I)

    def regulate_node(self, node):
        for k, v in node.attrs().items():
            if isinstance(v, str):
                v = strip_whitespace(v)
                if self.NULL_RE.match(v):
                    node[k] = ''
                else:
                    node[k] = v
