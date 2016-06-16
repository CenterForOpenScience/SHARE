import pytest

from share.models import ShareSource


@pytest.fixture
@pytest.mark.db
def share_source():
    source = ShareSource(name='tester')
    source.save()
    return source
