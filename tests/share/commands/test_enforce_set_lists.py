import pytest

from django.core.management import call_command

from tests import factories


@pytest.mark.django_db
class TestEnforceSetListsCommand:

    # --dry makes no changes
    # without --commit rolls back
    # without --whitelist only enforces blacklist
    # one source config
    # multiple source configs

    @pytest.fixture
    def source_config(self):
        return factories.SourceConfigFactory()

    @pytest.fixture
    def first_tags(self):
        return [
            factories.TagFactory(name='first1'),
            factories.TagFactory(name='first2'),
        ]

    @pytest.fixture
    def second_tags(self):
        return [
            factories.TagFactory(name='second1'),
            factories.TagFactory(name='second2'),
        ]

    @pytest.fixture
    def both_tags(self):
        return [
            factories.TagFactory(name='both1'),
            factories.TagFactory(name='both2'),
        ]

    @pytest.fixture
    def first_work(self, first_tags, both_tags, source_config):
        return self._create_work(first_tags + both_tags, source_config.source.user)

    @pytest.fixture
    def second_work(self, second_tags, both_tags, source_config):
        return self._create_work(second_tags + both_tags, source_config.source.user)

    def _create_work(self, tags, source_user):
        work = factories.AbstractCreativeWorkFactory()
        for tag in tags:
            through_tag = factories.ThroughTagsFactory(creative_work=work, tag=tag)
            through_tag.sources.add(source_user)
        work.sources.add(source_user)
        return work

    @pytest.mark.parametrize('whitelist,blacklist,enforce_whitelist,first_deleted,second_deleted', [
        ([], [], True, False, False),
        ([], [], False, False, False),
        (['first1'], [], True, False, True),
        (['first1'], [], False, False, False),
        (['something'], [], True, True, True),
        (['something'], [], False, False, False),
        ([], ['first1'], True, True, False),
        ([], ['second2'], False, False, True),
        ([], ['something'], True, False, False),
        ([], ['something'], False, False, False),
        (['both1', 'first1'], ['first2'], True, True, False),
        (['first1', 'second1'], ['both2'], False, True, True),
        (['first1', 'second1'], ['both2'], True, True, True),
        ([], ['first2', 'second2'], False, True, True),
    ])
    def test_enforce_set_lists(self, source_config, first_work, second_work, whitelist, blacklist, enforce_whitelist, first_deleted, second_deleted):
        source_config.transformer_kwargs = {
            'approved_sets': whitelist,
            'blocked_sets': blacklist
        }
        source_config.save()

        args = [source_config.label, '--commit']
        if enforce_whitelist:
            args.append('--whitelist')
        call_command('enforce_set_lists', *args)

        first_work.refresh_from_db()
        assert first_work.is_deleted == first_deleted

        second_work.refresh_from_db()
        assert second_work.is_deleted == second_deleted
