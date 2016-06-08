import pytest

from django.contrib.auth.models import User

from share.models import ShareUser


@pytest.fixture
@pytest.mark.db
def share_user():
    django_user = User()
    django_user.save()
    user = ShareUser(user=django_user)
    user.save()
    return user
