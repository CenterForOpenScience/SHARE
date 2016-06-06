import pytest

from share.models import ShareUser


@pytest.fixture
@pytest.mark.db
def share_user():
    user = ShareUser(short_id='testuser', full_name='Test User', is_entity=False)
    user.save()
    return user
