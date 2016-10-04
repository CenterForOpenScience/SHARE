import pytest

from share.models import Tag
from share.disambiguation import TagDisambiguator


class TestTag:

    @pytest.mark.django_db
    def test_disambiguates(self, change_ids):
        oldTag = Tag.objects.create(name='This', change_id=change_ids.get())
        disTag = TagDisambiguator('_:', {'name': 'This'}, Tag).find()

        assert disTag is not None
        assert disTag.id == oldTag.id
        assert disTag.name == oldTag.name

    @pytest.mark.django_db
    def test_does_not_disambiguate(self, change_ids):
        Tag.objects.create(name='This', change_id=change_ids.get())
        disTag = TagDisambiguator('_:', {'name': 'That'}, Tag).find()

        assert disTag is None


class TestThroughTags:

    def test_handles_unique_violation(self):
        pass

    def test_detects_existance(self):
        pass
