from unittest import mock

from share.search.index_strategy.trovesearch_denorm import (
    TrovesearchDenormIndexStrategy,
    task__delete_iri_value_scraps,
)

from . import _common_trovesearch_tests


class TestTrovesearchDenorm(_common_trovesearch_tests.CommonTrovesearchTests):
    def setUp(self):
        super().setUp()

        # make the followup delete task eager
        def _fake_apply_async(*args, **kwargs):
            self.index_strategy.pls_refresh()
            kwargs['countdown'] = 0  # don't wait
            task__delete_iri_value_scraps.apply(*args, **kwargs)
        self.enterContext(
            mock.patch.object(
                task__delete_iri_value_scraps,
                'apply_async',
                new=_fake_apply_async,
            )
        )

    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchDenormIndexStrategy('test_trovesearch_denorm')
