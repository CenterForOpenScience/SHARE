import pytest

from share.models import Tag
from share.models.meta import ThroughTags
from share.disambiguation import disambiguate


class TestTag:

    @pytest.mark.django_db
    def test_disambiguates(self, change_ids):
        oldTag = Tag.objects.create(name='This', change_id=change_ids.get())
        disTag = disambiguate('_:', {'name': 'This'}, Tag)

        assert disTag is not None
        assert disTag.id == oldTag.id
        assert disTag.name == oldTag.name

    @pytest.mark.django_db
    def test_does_not_disambiguate(self, change_ids):
        oldTag = Tag.objects.create(name='This', change_id=change_ids.get())
        disTag = disambiguate('_:', {'name': 'That'}, Tag)

        assert disTag is None


class TestThroughTags:

    def test_handles_unique_violation(self):
        pass

    def test_detects_existance(self):
        pass
