import unittest

from django.conf import settings
from primitive_metadata import primitive_rdf as rdf

from share.search import messages
from share.search.index_strategy.sharev2_elastic5 import Sharev2Elastic5IndexStrategy
from tests.share.search._util import create_indexcard
from trove.vocab.namespaces import DCTERMS, SHAREv2, RDF, BLARG
from ._with_real_services import RealElasticTestCase


@unittest.skipUnless(settings.ELASTICSEARCH5_URL, 'missing ELASTICSEARCH5_URL setting')
class TestSharev2Elastic5(RealElasticTestCase):
    # for RealElasticTestCase
    def get_index_strategy(self):
        index_strategy = Sharev2Elastic5IndexStrategy('test_sharev2_elastic5')
        if not index_strategy.STATIC_INDEXNAME.startswith('test_'):
            index_strategy.STATIC_INDEXNAME = f'test_{index_strategy.STATIC_INDEXNAME}'
        return index_strategy

    def setUp(self):
        super().setUp()
        self.__indexcard = create_indexcard(
            BLARG.hello,
            {
                BLARG.hello: {
                    RDF.type: {SHAREv2.CreativeWork},
                    DCTERMS.title: {rdf.literal('hello', language='en')},
                },
            },
            deriver_iris=[SHAREv2.sharev2_elastic],
        )

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

    # override RealElasticTestCase to match hacks done with assumptions
    # (single index that will not be updated again before being deleted)
    def _assert_happypath_until_ingest(self):
        # initial
        _index = next(self.index_strategy.each_subnamed_index())
        assert not _index.pls_check_exists()
        index_status = _index.pls_get_status()
        assert not index_status.creation_date
        assert not index_status.is_kept_live
        assert not index_status.is_default_for_searching
        assert not index_status.doc_count
        # create index
        _index.pls_create()
        assert _index.pls_check_exists()
        index_status = _index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live  # change from base class
        assert index_status.is_default_for_searching  # change from base class
        assert not index_status.doc_count
        # keep index live (with ingested updates)
        self.index_strategy.pls_start_keeping_live()  # now a no-op
        index_status = _index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert index_status.is_default_for_searching  # change from base class
        assert not index_status.doc_count
        # default index for searching
        self.index_strategy.pls_make_default_for_searching()  # now a no-op
        index_status = _index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert index_status.is_default_for_searching
        assert not index_status.doc_count
