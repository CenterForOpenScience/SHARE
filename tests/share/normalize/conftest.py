import pytest

from share.change import ChangeGraph
from tests.share.normalize.factories import Graph  # noqa


@pytest.fixture
def graph():
    return ChangeGraph([])
