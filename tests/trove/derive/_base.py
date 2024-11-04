import datetime
from unittest import mock, TestCase
import typing

from primitive_metadata import primitive_rdf as rdf

from ._inputs import DERIVER_TEST_DOCS, DeriverTestDoc


SHOULD_SKIP = object()  # for deriver inputs that should be skipped


class BaseIndexcardDeriverTest(TestCase):
    maxDiff = None

    #######
    # implement these things:

    # a subclass of IndexcardDeriver
    deriver_class: type

    # dictionary with the same keys as `DERIVER_TEST_DOCS` and values that
    # are either `SHOULD_SKIP` (above) or strings that will be passed as
    # `expected_text` to `derived_texts_equal`
    expected_outputs: dict

    # (optional override, for when equality isn't so easy)
    def assert_derived_texts_equal(self, expected_text: str, actual_text: str) -> None:
        self.assertEqual(expected_text, actual_text)

    #######
    # don't override anything else

    test_should_skip: typing.Callable[['BaseIndexcardDeriverTest'], None]
    test_derive_card_as_text: typing.Callable[['BaseIndexcardDeriverTest'], None]

    def __init_subclass__(cls):
        # add test methods on subclasses (but not the base class!)
        cls.test_should_skip = _test_should_skip
        cls.test_derive_card_as_text = _test_derive_card_as_text

    def setUp(self):
        _patcher = mock.patch('share.util.IDObfuscator.encode', new=lambda x: x.id)
        _patcher.start()
        self.addCleanup(_patcher.stop)

    def _get_deriver(self, input_doc: DeriverTestDoc):
        _mock_suid = mock.Mock()
        _mock_suid.id = '--suid_id--'
        _mock_suid.get_date_first_seen.return_value = datetime.datetime(2345, 1, 1)
        _mock_suid.get_backcompat_sharev2_suid.return_value = _mock_suid
        _mock_suid.identifier = '--sourceunique-id--'
        _mock_suid.source_config.label = '--sourceconfig-label--'
        _mock_suid.source_config.source.long_title = '--source-title--'

        _mock_indexcard_rdf = mock.Mock()
        _mock_indexcard_rdf.id = '--indexcardf-id--'
        _mock_indexcard_rdf.modified = datetime.datetime(2345, 2, 2)
        _mock_indexcard_rdf.as_rdfdoc_with_supplements.return_value = rdf.RdfGraph(input_doc.tripledict)
        _mock_indexcard_rdf.focus_iri = input_doc.focus_iri
        _mock_indexcard_rdf.from_raw_datum_id = '--rawdatum-id--'
        _mock_indexcard_rdf.indexcard.id = '--indexcard-id--'
        _mock_indexcard_rdf.indexcard.source_record_suid = _mock_suid
        return self.deriver_class(_mock_indexcard_rdf)

    def _iter_test_cases(self):
        for _input_key, _input_doc in DERIVER_TEST_DOCS.items():
            _expected_output = self.expected_outputs.get(_input_key)
            if _expected_output is None:
                raise NotImplementedError(f'{self.__class__.__qualname__}.expected_outputs["{_input_key}"]')
            with self.subTest(input_key=_input_key):
                yield (_input_key, self._get_deriver(_input_doc), _expected_output)


def _test_should_skip(self: BaseIndexcardDeriverTest) -> None:
    for _input_key, _deriver, _expected_output in self._iter_test_cases():
        self.assertEqual(
            bool(_expected_output is SHOULD_SKIP),
            _deriver.should_skip(),
        )


def _test_derive_card_as_text(self: BaseIndexcardDeriverTest) -> None:
    for _input_key, _deriver, _expected_output in self._iter_test_cases():
        if _expected_output is not SHOULD_SKIP:
            _output = _deriver.derive_card_as_text()
            self.assert_derived_texts_equal(_expected_output, _output)
