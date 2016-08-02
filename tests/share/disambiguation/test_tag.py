from share.models import Tag
from share.models import ThroughTags
from share.disambiguation import TagDisambiguator


def TagFactory(name):
    return Tag.objects.create(name=name)


class TestTag:

    def test_disambiguates(self):

        pass

    def test_does_not_disambiguate(self):
        pass


class TestThroughTags:

    def test_handles_unique_violation(self):
        pass

    def test_detects_existance(self):
        pass
