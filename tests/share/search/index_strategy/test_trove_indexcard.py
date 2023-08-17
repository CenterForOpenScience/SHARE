from tests import factories
from share.search import messages
from trove import models as trove_db
from trove.vocab.namespaces import RDFS
from ._with_real_services import RealElasticTestCase


class TestTroveIndexcard(RealElasticTestCase):
    # for RealElasticTestCase
    strategy_name_for_real = 'trove_indexcard'
    strategy_name_for_test = 'test_trove_indexcard'

    def setUp(self):
        super().setUp()
        self.__suid = factories.SourceUniqueIdentifierFactory()
        self.__raw = factories.RawDatumFactory(
            suid=self.__suid,
        )
        self.__indexcard = trove_db.Indexcard.objects.create(
            source_record_suid=self.__suid,
        )
        self.__indexcardf = trove_db.LatestIndexcardRdf.objects.create(
            from_raw_datum=self.__raw,
            indexcard=self.__indexcard,
            focus_iri='http://foo.example/hello',
            rdf_as_turtle=f'<http://foo.example/hello> <{RDFS.label}> "hello".',
            turtle_checksum_iri='foo',  # not enforced
        )

    def test_without_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.UPDATE_INDEXCARD,
            [self.__indexcard.id],
        )
        self._assert_happypath_without_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )

    def test_with_daemon(self):
        _messages_chunk = messages.MessagesChunk(
            messages.MessageType.UPDATE_INDEXCARD,
            [self.__indexcard.id],
        )
        self._assert_happypath_with_daemon(
            _messages_chunk,
            expected_doc_count=1,
        )
