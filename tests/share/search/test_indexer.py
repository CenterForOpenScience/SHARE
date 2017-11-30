import pytest

from share import models
from share.search import SearchIndexer

from tests import factories


class TestIdsToReindex:

    @pytest.mark.parametrize('model', [models.AbstractAgent, models.Tag, models.Source])
    @pytest.mark.parametrize('pks', [set(), {1}, {1, 2, 3}])
    def test_noops(self, model, pks):
        result = SearchIndexer(None).pks_to_reindex(model, pks)
        assert result == pks

    @pytest.mark.django_db
    def test_related_works(self):
        def part_of(child_work, parent_work):
            factories.AbstractWorkRelationFactory(
                type='share.ispartof',
                subject=child_work,
                related=parent_work
            )

        def retracts(retraction, work):
            factories.AbstractWorkRelationFactory(
                type='share.retracts',
                subject=retraction,
                related=work
            )

        child = factories.AbstractCreativeWorkFactory()
        lost_sibling = factories.AbstractCreativeWorkFactory(is_deleted=True)
        parent = factories.AbstractCreativeWorkFactory()
        gparent = factories.AbstractCreativeWorkFactory()
        ggparent = factories.AbstractCreativeWorkFactory()
        gggparent = factories.AbstractCreativeWorkFactory()

        retraction = factories.AbstractCreativeWorkFactory()

        part_of(child, parent)
        part_of(lost_sibling, parent)
        part_of(parent, gparent)
        part_of(gparent, ggparent)
        part_of(ggparent, gggparent)
        retracts(retraction, child)

        cases = [
            ({child}, {child}),
            ({lost_sibling}, {lost_sibling}),
            ({parent}, {parent, child}),
            ({gparent}, {gparent, parent, child}),
            ({ggparent}, {ggparent, gparent, parent, child}),
            ({gggparent}, {gggparent, ggparent, gparent, parent}),
            ({retraction}, {retraction, child}),
            ({retraction, ggparent}, {retraction, ggparent, gparent, parent, child}),
        ]

        for input, expected in cases:
            input_ids = {w.id for w in input}
            expected_ids = {w.id for w in expected}
            actual_ids = SearchIndexer(None).pks_to_reindex(models.AbstractCreativeWork, input_ids)
            assert expected_ids == actual_ids
