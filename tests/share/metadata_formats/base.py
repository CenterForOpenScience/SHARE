import pytest

from share.models.core import FormattedMetadataRecord
from share.util.extensions import Extensions

from tests import factories
from .conftest import FORMATTER_TEST_INPUTS


@pytest.mark.usefixtures('nested_django_db')
class BaseMetadataFormatterTest:

    ####### override these things #######

    # formatter key, as registered in setup.py
    formatter_key = None

    # dictionary with the same keys as `FORMATTER_TEST_INPUTS`, mapping to values
    # that `assert_formatter_outputs_equal` will understand
    expected_outputs = {}

    def assert_formatter_outputs_equal(self, actual_output, expected_output):
        """raise AssertionError if the two outputs aren't equal

        @param actual_output (str): return value of the formatter's `.format()` method
        @param expected_output: corresponding value from this class's `expected_outputs` dictionary
        """
        raise NotImplementedError

    ####### don't override anything else #######

    @pytest.fixture(scope='session', autouse=True)
    def _sanity_check(self):
        assert FORMATTER_TEST_INPUTS.keys() == self.expected_outputs.keys(), f'check the test class\'s `expected_outputs` matches {__name__}.FORMATTER_TEST_INPUTS'

    @pytest.fixture(scope='class')
    def formatter(self):
        return Extensions.get('share.metadata_formats', self.formatter_key)()

    @pytest.fixture(scope='class')
    def expected_output(self, _test_key):
        return self.expected_outputs[_test_key]

    @pytest.fixture(scope='class')
    def source(self, formatter_test_input, class_scoped_django_db, request):
        print(f'>>> source ({request.node})')
        return factories.SourceFactory(long_title=formatter_test_input['source_name'])

    @pytest.fixture(scope='class')
    def source_config(self, source, formatter_test_input, class_scoped_django_db):
        return factories.SourceConfigFactory(
            label=formatter_test_input['source_config_label'],
            source=source,
        )

    @pytest.fixture(scope='class')
    def suid(self, source_config, formatter_test_input, class_scoped_django_db):
        return factories.SourceUniqueIdentifierFactory(
            id=formatter_test_input['suid_id'],
            identifier=formatter_test_input['suid_value'],
            source_config=source_config,
        )

    @pytest.fixture(scope='class')
    def normalized_datum(self, suid, source, formatter_test_input, class_scoped_django_db):
        return factories.NormalizedDataFactory(
            raw=factories.RawDatumFactory(
                **formatter_test_input['raw_datum_kwargs'],
                suid=suid,
            ),
            **formatter_test_input['normalized_datum_kwargs'],
            source__source=source,
        )

    def test_formatter(self, formatter, normalized_datum, expected_output):
        actual_output = formatter.format(normalized_datum)
        self.assert_formatter_outputs_equal(actual_output, expected_output)

    def test_save_formatted_records(self, normalized_datum, expected_output):
        saved_records = FormattedMetadataRecord.objects.save_formatted_records(
            suid=normalized_datum.raw.suid,
            record_formats=[self.formatter_key],
            normalized_datum=normalized_datum,
        )
        if expected_output is None:
            assert len(saved_records) == 0
        else:
            assert len(saved_records) == 1
            actual_output = saved_records[0].formatted_metadata
            self.assert_formatter_outputs_equal(actual_output, expected_output)
