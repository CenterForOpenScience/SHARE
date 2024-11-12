import json

from tests import factories
from share.search import messages
from share.search.index_strategy.sharev2_elastic8 import Sharev2Elastic8IndexStrategy
from share.util import IDObfuscator
from ._with_real_services import RealElasticTestCase


class TestSharev2Elastic8(RealElasticTestCase):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return Sharev2Elastic8IndexStrategy('test_sharev2_elastic8')

    def setUp(self):
        super().setUp()
        self.__suid = factories.SourceUniqueIdentifierFactory()
        self.__fmr = factories.FormattedMetadataRecordFactory(
            suid=self.__suid,
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({
                'id': IDObfuscator.encode(self.__suid),
                'title': 'hello',
            })
        )

    def test_without_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [self.__suid.id],
        )
        self._assert_happypath_without_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_with_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [self.__suid.id],
        )
        self._assert_happypath_with_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )
