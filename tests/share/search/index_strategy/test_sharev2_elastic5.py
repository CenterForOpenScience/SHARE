import json

from tests import factories
from share.util import IDObfuscator
from ._with_real_services import RealElasticTestCase


class TestSharev2Elastic5(RealElasticTestCase):
    # abstract method from RealElasticTestCase
    def get_real_strategy_name(self):
        return 'sharev2_elastic5'

    # abstract method from RealElasticTestCase
    def get_test_strategy_name(self):
        return 'test_sharev2_elastic5'

    # override method from RealElasticTestCase
    def get_index_strategy(self):
        index_strategy = super().get_index_strategy()
        index_strategy.STATIC_INDEXNAME = f'test_{index_strategy.STATIC_INDEXNAME}'
        return index_strategy

    # abstract method from RealElasticTestCase
    def get_formatted_record(self):
        suid = factories.SourceUniqueIdentifierFactory()
        return factories.FormattedMetadataRecordFactory(
            suid=suid,
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({
                'id': IDObfuscator.encode(suid),
                'title': 'hello',
            })
        )

    def test_without_daemon(self):
        self._assert_happypath_without_daemon()

    def test_with_daemon(self):
        self._assert_happypath_with_daemon()

    # override RealElasticTestCase to match hacks done with assumptions
    # (single index that will not be updated again before being deleted)
    def _assert_happypath_until_ingest(self):
        # initial
        assert not self.current_index.pls_check_exists()
        index_status = self.current_index.pls_get_status()
        assert not index_status.creation_date
        assert not index_status.is_kept_live
        assert not index_status.is_default_for_searching
        assert not index_status.doc_count
        # create index
        self.current_index.pls_create()
        assert self.current_index.pls_check_exists()
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live  # change from base class
        assert index_status.is_default_for_searching  # change from base class
        assert not index_status.doc_count
        # keep index live (with ingested updates)
        self.current_index.pls_start_keeping_live()  # now a no-op
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert index_status.is_default_for_searching  # change from base class
        assert not index_status.doc_count
        # default index for searching
        self.index_strategy.pls_make_default_for_searching(self.current_index)  # now a no-op
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert index_status.is_default_for_searching
        assert not index_status.doc_count
