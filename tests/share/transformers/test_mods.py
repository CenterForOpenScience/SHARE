import pytest

from share.legacy_normalize.transformers.mods import MODSTransformer

from tests.share.transformers.test_oai_dc import TestSetsFilter


class TestModsSetsFilter(TestSetsFilter):

    TRANSFORMER_CLASS = MODSTransformer

    @pytest.fixture
    def datum(self):
        return '''
<record xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <header>
  <identifier>urn:identifier</identifier>
    <datestamp>2017-10-11T01:00:12Z</datestamp>
    <setSpec>set1</setSpec>
    <setSpec>set2</setSpec>
  </header>
  <metadata>
    <mods:mods xmlns:mods="http://www.loc.gov/mods/v3" xmlns:doc="http://www.lyncode.com/xoai" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-1.xsd">
      <mods:name>
        <mods:namePart>Greg Universe</mods:namePart>
      </mods:name>
      <mods:originInfo>
        <mods:dateIssued encoding="iso8601">2017-03</mods:dateIssued>
      </mods:originInfo>
      <mods:abstract>Abstract abstract</mods:abstract>
      <mods:language>
        <mods:languageTerm>en</mods:languageTerm>
      </mods:language>
      <mods:titleInfo>
        <mods:title>Title title title</mods:title>
      </mods:titleInfo>
      <mods:genre>Presentation</mods:genre>
    </mods:mods>
  </metadata>
</record>
    '''
