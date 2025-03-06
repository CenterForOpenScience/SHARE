from primitive_metadata import primitive_rdf as rdf

from share.search import messages
from share.search.index_strategy.sharev2_elastic8 import Sharev2Elastic8IndexStrategy
from trove.vocab.namespaces import DCTERMS, SHAREv2
from tests.share.search._util import create_indexcard
from ._with_real_services import RealElasticTestCase


BLARG = rdf.IriNamespace('http://blarg.example/')


class TestSharev2Elastic8(RealElasticTestCase):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return Sharev2Elastic8IndexStrategy('test_sharev2_elastic8')

    def setUp(self):
        super().setUp()
        self.__indexcard = create_indexcard(
            BLARG.hello,
            {
                BLARG.hello: {
                    DCTERMS.title: {rdf.Literal('hello', language='en')},
                },
            },
            deriver_iris=[SHAREv2.sharev2_elastic],
        )

    def test_without_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [self.__indexcard.source_record_suid_id],
        )
        self._assert_happypath_without_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_with_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [self.__indexcard.source_record_suid_id],
        )
        self._assert_happypath_with_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )
