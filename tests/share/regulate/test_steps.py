import pytest

from share.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.util.extensions import Extensions


@pytest.mark.parametrize('namespace, base_class', [
    ('share.regulate.node_steps', NodeStep),
    ('share.regulate.graph_steps', GraphStep),
    ('share.regulate.validation_steps', ValidationStep),
])
def test_step_bases(namespace, base_class):
    assert all(issubclass(e.plugin, base_class) for e in Extensions._load_namespace(namespace))
