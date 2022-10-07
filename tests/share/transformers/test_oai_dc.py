import pytest

from share.models import SourceConfig
from share.legacy_normalize.transformers.oai import OAITransformer


class TestSetsFilter:

    TRANSFORMER_CLASS = OAITransformer

    @pytest.fixture
    def datum(self):
        return '''
<record xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <header>
    <identifier>urn:identifier</identifier>
    <datestamp>2017-09-12T13:35:17Z</datestamp>
    <setSpec>set1</setSpec>
    <setSpec>set2</setSpec>
  </header>
  <metadata>
    <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
      <dc:title>Title title title</dc:title>
      <dc:creator>Greg Universe</dc:creator>
      <dc:description></dc:description>
      <dc:date>2017-09-11T03:13:21Z</dc:date>
      <dc:type>article</dc:type>
    </oai_dc:dc>
  </metadata>
</record>
        '''.strip()

    @pytest.mark.parametrize('approved_sets, blocked_sets, expect_allowed', [
        (None, None, True),
        ([], [], True),
        (['set1'], None, True),
        (['set2'], None, True),
        (None, ['set1'], False),
        (None, ['set2'], False),
        (['other'], [], False),
        ([], ['foo', 'bar'], True),
        (['set1'], ['set1'], False),
        (['set1'], ['set2'], False),
        (['one', 'two'], ['three', 'four'], False),
        (['one', 'two', 'set2'], ['three', 'four'], True),
        (['one', 'two'], ['three', 'four', 'set1'], False),
    ])
    def test_sets(self, datum, approved_sets, blocked_sets, expect_allowed):
        source_config = SourceConfig(transformer_kwargs={
            'approved_sets': approved_sets,
            'blocked_sets': blocked_sets
        })
        transformer = self.TRANSFORMER_CLASS(source_config)
        res = transformer.transform(datum)
        if expect_allowed:
            assert res is not None
        else:
            assert res is None
