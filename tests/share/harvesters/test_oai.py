import pytest
from unittest import mock

from lxml import etree

from share.harvesters.oai import OAIHarvester

from tests import factories


@pytest.mark.django_db
class TestOAIHarvester:

    OAI_DC_RECORD = etree.fromstring('''
    <record xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
             xmlns:dc="http://purl.org/dc/elements/1.1/"
             xmlns="http://www.openarchives.org/OAI/2.0/"
             xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <header>
            <identifier>oai:philpapers.org/rec/SILGGG</identifier>
            <datestamp>2017-01-29T15:25:15Z</datestamp>
          </header>
          <metadata>
            <oai_dc:dc xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
              <dc:title>Good government, Governance and Human Complexity. Luigi Einaudi’s Legacy and Contemporary Society</dc:title>
              <dc:type>info:eu-repo/semantics/book</dc:type>
              <dc:creator>Silvestri, Paolo</dc:creator>
              <dc:creator>Heritier, Paolo</dc:creator>
              <dc:subject>Philosophy</dc:subject>
              <dc:description>The book presents an interdisciplinary exploration aimed at renewing interest in Luigi Einaudi’s search for “good government”, broadly understood as “good society”. Prompted by the Einaudian quest, the essays - exploring philosophy of law, economics, politics and epistemology - develop the issue of good government in several forms, including  the relationship between public and private, public governance, the question of freedom and the complexity of the human in contemporary societies.</dc:description>
              <dc:date>2012</dc:date>
              <dc:identifier>https://philpapers.org/rec/SILGGG</dc:identifier>
              <dc:language>en</dc:language>
            </oai_dc:dc>
          </metadata>
          <about>
            <rights xmlns="http://www.openarchives.org/OAI/2.0/rights/"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/rights/ http://www.openarchives.org/OAI/2.0/rights.xsd">
              <rightsReference xmlns="">https://philpapers.org/help/terms.html</rightsReference>
            </rights>
          </about>
        </record>
    ''')

    def test_duplicate_resumption_tokens(self, monkeypatch):
        harvester = OAIHarvester(factories.SourceConfigFactory(), metadata_prefix='oaidc')
        monkeypatch.setattr(harvester, 'fetch_page', mock.Mock(return_value=([self.OAI_DC_RECORD], 'token')))

        records = []
        with pytest.raises(ValueError) as e:
            for x in harvester.fetch_records(''):
                records.append(x)

        assert len(records) == 1
        assert e.value.args == ('Found duplicate resumption token "token" from {!r}'.format(harvester), )

    def test_resumption_tokens(self, monkeypatch):
        harvester = OAIHarvester(factories.SourceConfigFactory(), metadata_prefix='oaidc')
        monkeypatch.setattr(harvester, 'fetch_page', mock.Mock(side_effect=(
            ([self.OAI_DC_RECORD], 'token'),
            ([self.OAI_DC_RECORD], None),
        )))

        assert len(list(harvester.fetch_records(''))) == 2
