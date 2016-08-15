import pytest

from share.models import Tag
from share.models.meta import ThroughTags
from share.disambiguation import disambiguate


def create_tag(name, change_id):
    return Tag.objects.create(name=name, change_id=change_id)


class TestTag:

    @pytest.mark.django_db
    def test_disambiguates(self, change_id):
        oldTag = create_tag('This', change_id)
        disTag = disambiguate('_:', {'name': 'This'}, Tag)

        assert disTag is not None
        assert disTag.id == oldTag.id
        assert disTag.name == oldTag.name

    @pytest.mark.django_db
    def test_does_not_disambiguate(self, change_id):
        oldTag = create_tag('This', change_id)
        disTag = disambiguate('_:', {'name': 'That'}, Tag)

        assert disTag is None


class TestThroughTags:

    def test_handles_unique_violation(self):
        pass

    def test_detects_existance(self):
        pass
