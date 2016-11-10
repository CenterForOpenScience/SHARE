import pytest

from share.change import ChangeGraph


@pytest.fixture
def graph():
    return ChangeGraph([])
