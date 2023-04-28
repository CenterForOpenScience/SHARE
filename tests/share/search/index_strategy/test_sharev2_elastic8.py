import json

from tests import factories
from ._with_real_services import RealElasticTestCase


class TestSharev2Elastic8(RealElasticTestCase):
    # abstract method from RealElasticTestCase
    def get_real_strategy_name(self):
        return 'sharev2_elastic8'

    # abstract method from RealElasticTestCase
    def get_test_strategy_name(self):
        return 'test_sharev2_elastic8'

    # abstract method from RealElasticTestCase
    def get_formatted_record(self):
        return factories.FormattedMetadataRecordFactory(
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({'title': 'hello'})
        )

    def test_without_daemon(self):
        self._assert_happypath_without_daemon()

    def test_with_daemon(self):
        self._assert_happypath_with_daemon()
