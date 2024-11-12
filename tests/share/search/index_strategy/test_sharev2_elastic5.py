import json
import unittest

from django.conf import settings

from tests import factories
from share.search import messages
from share.search.index_strategy.sharev2_elastic5 import Sharev2Elastic5IndexStrategy
from share.util import IDObfuscator
from ._with_real_services import RealElasticTestCase


@unittest.skipUnless(settings.ELASTICSEARCH5_URL, 'missing ELASTICSEARCH5_URL setting')
class TestSharev2Elastic5(RealElasticTestCase):
    # for RealElasticTestCase
    def get_index_strategy(self):
        index_strategy = Sharev2Elastic5IndexStrategy('test_sharev2_elastic5')
        if not index_strategy.STATIC_INDEXNAME.startswith('test_'):
            index_strategy.STATIC_INDEXNAME = f'test_{index_strategy.STATIC_INDEXNAME}'
        return index_strategy

    def test_without_daemon(self):
        _formatted_record = self._get_formatted_record()
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [_formatted_record.suid_id],
        )
        self._assert_happypath_without_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_with_daemon(self):
        _formatted_record = self._get_formatted_record()
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [_formatted_record.suid_id],
        )
        self._assert_happypath_with_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def _get_formatted_record(self):
        suid = factories.SourceUniqueIdentifierFactory()
        return factories.FormattedMetadataRecordFactory(
            suid=suid,
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({
                'id': IDObfuscator.encode(suid),
                'title': 'hello',
            })
        )

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
