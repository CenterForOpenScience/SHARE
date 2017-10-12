import pytest

from share.models import SourceConfig
from share.transformers.oai import OAITransformer


class TestSetsFilter:

    TRANSFORMER_CLASS = OAITransformer

    @pytest.fixture
    def datum(self):
        return '''
<record xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <header>
    <identifier>oai:share.osf.io:461B6-A5C-956</identifier>
    <datestamp>2017-09-12T13:35:17Z</datestamp>
    <setSpec>au.uow</setSpec>
  </header>
  <metadata>
    <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
      <dc:title>
            Ammonium aminodiboranate: A long-sought isomer of diammoniate of diborane and ammonia borane dimer
            </dc:title>
      <dc:creator>Chen, Weidong</dc:creator>
      <dc:creator>Yu, Haibo</dc:creator>
      <dc:creator>Wu, Guotao</dc:creator>
      <dc:creator>He, Teng</dc:creator>
      <dc:creator>Li, Zhao</dc:creator>
      <dc:creator>Guo, Zaiping</dc:creator>
      <dc:creator>Liu, Hua-Kun</dc:creator>
      <dc:creator>Huang, Zhenguo</dc:creator>
      <dc:creator>Chen, Ping</dc:creator>
      <dc:subject>Physical Sciences and Mathematics</dc:subject>
      <dc:subject>Engineering</dc:subject>
      <dc:description>
            Ammonium aminodiboranate ([NH4][BH3NH2BH3]) is a long-sought isomer of diammoniate of diborane ([NH3BH2NH3][BH4]) and ammonia borane (NH3BH3) dimer. Our results show that [NH4][BH3NH2BH3] is stable in tetrahydrofuran at -18&#xB0;C and decomposes rapidly to NH3BH2NH2BH3 and H2 at elevated temperatures. The decomposition pathway is dictated by the dihydrogen bonding between H&#x3B4;+ on NH4 + and H&#x3B4;- on BH3, as confirmed by theoretical calculations. This is in contrast to the interconversion between [NH3BH2NH3][BH4] and (NH3BH3)2, although all three have dihydrogen bonds and the same stoichiometry.
            </dc:description>
      <dc:publisher>Research Online</dc:publisher>
      <dc:publisher>Department of History</dc:publisher>
      <dc:date>2017-09-11T03:13:21Z</dc:date>
      <dc:type>article</dc:type>
      <dc:identifier>http://ro.uow.edu.au/aiimpapers/2062</dc:identifier>
      <dc:identifier>oai://ro.uow.edu.au/aiimpapers-3064</dc:identifier>
    </oai_dc:dc>
  </metadata>
</record>
        '''.strip()

    @pytest.mark.parametrize('approved_sets, blocked_sets, allowed', [
        (None, None, True),
        ([], [], True),
        (['au.uow'], None, True),
        (None, ['au.uow'], False),
        (['uow'], [], False),
        ([], ['foo', 'bar'], True),
        (['au.uow'], ['au.uow'], False),
        (['one', 'two'], ['three', 'four'], False),
        (['one', 'two', 'au.uow'], ['three', 'four'], True),
        (['one', 'two'], ['three', 'four', 'au.uow'], False),
    ])
    def test_sets(self, datum, approved_sets, blocked_sets, allowed):
        source_config = SourceConfig(transformer_kwargs={
            'approved_sets': approved_sets,
            'blocked_sets': blocked_sets
        })
        transformer = self.TRANSFORMER_CLASS(source_config, **source_config.transformer_kwargs)
        res = transformer.transform(datum)
        if allowed:
            assert res is not None
        else:
            assert res is None
