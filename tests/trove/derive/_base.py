import datetime
from unittest import mock

from primitive_metadata import primitive_rdf as rdf

from trove.derive._base import IndexcardDeriver
from tests.trove._input_output_tests import BasicInputOutputTestCase
from ._inputs import DERIVER_TEST_DOCS, DeriverTestDoc


SHOULD_SKIP = object()  # for deriver inputs that should be skipped


class BaseIndexcardDeriverTest(BasicInputOutputTestCase):
    inputs = DERIVER_TEST_DOCS  # (leave this one alone)

    # required on subclasses: `deriver_class` and `expected_outputs`
    deriver_class: type[IndexcardDeriver]
    # expected_outputs: dict[str, typing.Any]
    # ^ (from BasicInputOutputTestCase) must have the same keys as
    # `DERIVER_TEST_DOCS` and values that are either `SHOULD_SKIP`
    # (when `deriver.should_skip()` should return true) or a value
    # that can be compared against `deriver.derive_card_as_text()`

    def compute_output(self, given_input):
        return self._get_deriver(given_input).derive_card_as_text()

    def run_input_output_test(self, given_input, expected_output):
        if expected_output is SHOULD_SKIP:
            self.assertTrue(self._get_deriver(given_input).should_skip())
        else:
            super().run_input_output_test(given_input, expected_output)

    def _get_deriver(self, input_doc: DeriverTestDoc):
        _mock_suid = mock.Mock()
        _mock_suid.id = '--suid_id--'
        _mock_suid.get_date_first_seen.return_value = datetime.datetime(2345, 1, 1)
        _mock_suid.get_backcompat_sharev2_suid.return_value = _mock_suid
        _mock_suid.identifier = '--sourceunique-id--'
        _mock_suid.source_config.label = '--sourceconfig-label--'
        _mock_suid.source_config.source.long_title = '--source-title--'

        _mock_resource_description = mock.Mock()
        _mock_resource_description.id = '--resdes-id--'
        _mock_resource_description.modified = datetime.datetime(2345, 2, 2)
        _mock_resource_description.as_rdfdoc_with_supplements.return_value = rdf.RdfGraph(input_doc.tripledict)
        _mock_resource_description.focus_iri = input_doc.focus_iri
        _mock_resource_description.indexcard.id = '--indexcard-id--'
        _mock_resource_description.indexcard.source_record_suid = _mock_suid
        return self.deriver_class(_mock_resource_description)
