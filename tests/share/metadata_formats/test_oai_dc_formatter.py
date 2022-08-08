from lxml import etree

from tests.share.metadata_formats.base import BaseMetadataFormatterTest


def xml_elements_equal(element_1, element_2):
    return (
        element_1.tag == element_2.tag
        and element_1.text == element_2.text
        and element_1.tail == element_2.tail
        and element_1.attrib == element_2.attrib
        and len(element_1) == len(element_2)
        and all(
            xml_elements_equal(child_1, child_2)
            for child_1, child_2 in zip(element_1, element_2)
        )
    )


class TestOaiDcFormatter(BaseMetadataFormatterTest):
    formatter_key = 'oai_dc'

    def assert_formatter_outputs_equal(self, actual_output, expected_output):
        if expected_output is None:
            assert actual_output is None
        else:
            xml_parser = etree.XMLParser(remove_blank_text=True)
            actual_xml = etree.fromstring(actual_output, parser=xml_parser)
            expected_xml = etree.fromstring(expected_output, parser=xml_parser)
            assert xml_elements_equal(actual_xml, expected_xml), f"actual: {etree.tostring(actual_xml, encoding='unicode', pretty_print=True)}\nexpected: {etree.tostring(expected_xml, encoding='unicode', pretty_print=True)}"

    expected_outputs = {
        'mycorrhizas': '''
        <oai_dc:dc
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        >
            <dc:title>The Role of Mycorrhizas in Forest Soil Stability with Climate Change</dc:title>
            <dc:creator>Suzanne Simard</dc:creator>
            <dc:creator>Mary Austi</dc:creator>
            <dc:publisher>InTech</dc:publisher>
            <dc:date>2017-03-31T05:39:48Z</dc:date>
            <dc:type>creativework</dc:type>
            <dc:identifier>http://dx.doi.org/10.5772/9813</dc:identifier>
        </oai_dc:dc>
        ''',
        'no-names-only-name-parts': '''
        <oai_dc:dc
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        >
            <dc:title>The Role of Mycorrhizas in Forest Soil Stability with Climate Change</dc:title>
            <dc:creator>Suzanne Simard</dc:creator>
            <dc:creator>Mary Austi</dc:creator>
            <dc:date>2017-03-31T05:39:48Z</dc:date>
            <dc:type>creativework</dc:type>
            <dc:identifier>http://dx.doi.org/10.5772/9813</dc:identifier>
        </oai_dc:dc>
        ''',
        'with-is_deleted': None,
        'with-subjects': '''
        <oai_dc:dc
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        >
          <dc:title>Assorted chair</dc:title>
          <dc:creator>Some Rando</dc:creator>
          <dc:subject>Architecture</dc:subject>
          <dc:subject>Business</dc:subject>
          <dc:subject>Custom biologyyyy</dc:subject>
          <dc:subject>Education</dc:subject>
          <dc:date>2019-01-23T20:34:21Z</dc:date>
          <dc:type>registration</dc:type>
          <dc:identifier>http://staging.osf.io/chair/</dc:identifier>
          <dc:relation>http://staging.osf.io/vroom/</dc:relation>
        </oai_dc:dc>
        ''',
        'with-osf-extra': '''
        <oai_dc:dc
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        >
          <dc:title>So open</dc:title>
          <dc:creator>Open McOperton</dc:creator>
          <dc:date>2017-03-31T05:39:48Z</dc:date>
          <dc:type>creativework</dc:type>
          <dc:identifier>https://example.com/open</dc:identifier>
        </oai_dc:dc>
        ''',
    }
