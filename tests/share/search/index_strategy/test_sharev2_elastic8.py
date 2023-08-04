import json

from tests import factories
from share.search import messages
from share.util import IDObfuscator
from ._with_real_services import RealElasticTestCase


class TestSharev2Elastic8(RealElasticTestCase):
    # abstract method from RealElasticTestCase
    def get_real_strategy_name(self):
        return 'sharev2_elastic8'

    # abstract method from RealElasticTestCase
    def get_test_strategy_name(self):
        return 'test_sharev2_elastic8'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.__suid = factories.SourceUniqueIdentifierFactory()
        cls.__fmr = factories.FormattedMetadataRecordFactory(
            suid=cls.__suid,
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({
                'id': IDObfuscator.encode(cls.__suid),
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
