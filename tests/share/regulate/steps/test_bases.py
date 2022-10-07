import pytest

from share.legacy_normalize.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.util.extensions import Extensions


@pytest.mark.parametrize('namespace, base_class', [
    ('share.regulate.steps.node', NodeStep),
    ('share.regulate.steps.graph', GraphStep),
    ('share.regulate.steps.validate', ValidationStep),
])
def test_step_bases(namespace, base_class):
    assert all(issubclass(e.plugin, base_class) for e in Extensions._load_namespace(namespace))
