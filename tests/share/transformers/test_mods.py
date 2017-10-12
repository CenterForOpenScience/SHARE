import pytest

from share.transformers.mods import MODSTransformer

from tests.share.transformers.test_oai_dc import TestSetsFilter


class TestModsSetsFilter(TestSetsFilter):
    TRANSFORMER_CLASS = MODSTransformer

    @pytest.fixture
    def datum(self):
        return '''
<record xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <header>
    <identifier>oai:researchspace.csir.co.za:10204/9653</identifier>
    <datestamp>2017-10-11T01:00:12Z</datestamp>
    <setSpec>au.uow</setSpec>
  </header>
  <metadata>
    <mods:mods xmlns:mods="http://www.loc.gov/mods/v3" xmlns:doc="http://www.lyncode.com/xoai" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-1.xsd">
      <mods:name>
        <mods:namePart>G&#xF6;r&#xFC;r, OC</mods:namePart>
      </mods:name>
      <mods:name>
        <mods:namePart>Rosman, Benjamin S</mods:namePart>
      </mods:name>
      <mods:name>
        <mods:namePart>Hoffman, G</mods:namePart>
      </mods:name>
      <mods:name>
        <mods:namePart>Albayrak, S</mods:namePart>
      </mods:name>
      <mods:extension>
        <mods:dateAvailable encoding="iso8601">2017-10-10T10:29:27Z</mods:dateAvailable>
      </mods:extension>
      <mods:extension>
        <mods:dateAccessioned encoding="iso8601">2017-10-10T10:29:27Z</mods:dateAccessioned>
      </mods:extension>
      <mods:originInfo>
        <mods:dateIssued encoding="iso8601">2017-03</mods:dateIssued>
      </mods:originInfo>
      <mods:identifier type="citation">G&#xF6;r&#xFC;r, O.C., Rosman, B.S., Hoffman, G. et al. 2017. Toward integrating Theory of Mind into adaptive decision-making of social robots to understand human intention. Workshop on the Role of Intentions in Human-Robot Interaction at the International Conference on Human-Robot Interaction, 6 March 2017, Vienna, Austria</mods:identifier>
      <mods:identifier type="uri">http://intentions.xyz/wp-content/uploads/2017/01/Gorur.gorur_HRI17_wsInt_camReady.pdf</mods:identifier>
      <mods:identifier type="uri">https://www.researchgate.net/publication/314238744_Toward_Integrating_Theory_of_Mind_into_Adaptive_Decision-_Making_of_Social_Robots_to_Understand_Human_Intention</mods:identifier>
      <mods:identifier type="uri">http://hdl.handle.net/10204/9653</mods:identifier>
      <mods:abstract>We propose an architecture that integrates Theory of Mind into a robot&#x2019;s decision-making to infer a human&#x2019;s intention and adapt to it. The architecture implements humanrobot collaborative decision-making for a robot incorporating human variability in their emotional and intentional states. This research first implements a mechanism for stochastically estimating a human&#x2019;s belief over the state of the actions that the human could possibly be executing. Then, we integrate this information into a novel stochastic human-robot shared planner that models the human&#x2019;s preferred plan. Our contribution lies in the ability of our model to handle the conditions: 1) when the human&#x2019;s intention is estimated incorrectly and the true intention may be unknown to the robot, and 2) when the human&#x2019;s intention is estimated correctly but the human doesn&#x2019;t want the robot&#x2019;s assistance in the given context. A robot integrating this model into its decision-making process would better understand a human&#x2019;s need for assistance and therefore adapt to behave less intrusively and more reasonably in assisting its human companion.</mods:abstract>
      <mods:language>
        <mods:languageTerm>en</mods:languageTerm>
      </mods:language>
      <mods:subject>
        <mods:topic>Theory of mind</mods:topic>
      </mods:subject>
      <mods:subject>
        <mods:topic>Social robots</mods:topic>
      </mods:subject>
      <mods:subject>
        <mods:topic>Human intention understanding</mods:topic>
      </mods:subject>
      <mods:titleInfo>
        <mods:title>Toward integrating Theory of Mind into adaptive decision-making of social robots to understand human intention</mods:title>
      </mods:titleInfo>
      <mods:genre>Presentation</mods:genre>
    </mods:mods>
  </metadata>
</record>
    '''
