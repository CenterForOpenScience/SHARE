from tests.share.metadata_formats.base import FORMATTER_TEST_INPUTS
from tests.share.metadata_formats.test_oai_dc_formatter import TestOaiDcFormatter as oaidc_test_cases


class TestPlsRenderMetadata:
    def _get_test_keys(self):
        return FORMATTER_TEST_INPUTS.keys()

    def _get_input(self, test_key):
        return FORMATTER_TEST_INPUTS[test_key]['normalized_datum_kwargs']['data']

    def _get_expected_output(self, test_key):
        return oaidc_test_cases.expected_outputs[test_key]

    def test_works(self, client):
        for test_key in self._get_test_keys():
            try:
                resp = client.post(
                    '/api/v2/pls-render-metadata',
                    self._get_input(test_key),
                )
                assert resp.status_code == 200
                assert resp.json() == self._get_expected_output(test_key)
                print(f'success! ({test_key})')
            except Exception as e:
                print(f'fail! ({test_key}, {e})')
