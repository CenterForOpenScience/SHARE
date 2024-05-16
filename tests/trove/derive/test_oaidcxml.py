from trove.derive.oaidc_xml import OaiDcXmlDeriver

from ._base import BaseIndexcardDeriverTest, SHOULD_SKIP


class TestOaiDcXmlDeriver(BaseIndexcardDeriverTest):
    deriver_class = OaiDcXmlDeriver

    expected_outputs = {
        'blarg-item': SHOULD_SKIP,
        'blarg-project': (
            '<oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">'
            '<dc:title xml:lang="en">title</dc:title>'
            '<dc:date>2024-02-14T00:00:00Z</dc:date>'
            '<dc:type>Project</dc:type>'
            '</oai_dc:dc>'
        ),
        'sharev2-with-subjects': (
            '<oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">'
            '<dc:title>Assorted chair</dc:title>'
            '<dc:creator>Some Rando</dc:creator>'
            '<dc:date>2019-01-23T00:00:00Z</dc:date>'
            '<dc:type>CreativeWork</dc:type>'
            '<dc:type>Publication</dc:type>'
            '<dc:type>Registration</dc:type>'
            '<dc:identifier>http://osf.example/chair/</dc:identifier>'
            '<dc:relation>http://osf.example/vroom/</dc:relation>'
            '</oai_dc:dc>'
        ),
        'osfmap-registration': (
            '<oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">'
            '<dc:title>IA/IMLS Demo</dc:title>'
            '<dc:creator>JW</dc:creator>'
            '<dc:subject>Education</dc:subject>'
            '<dc:description>This registration tree is intended to demonstrate linkages between the OSF view of a Registration and the Internet Archive view</dc:description>'
            '<dc:publisher>OSF Registries</dc:publisher>'
            '<dc:date>2021-10-18T00:00:00Z</dc:date>'
            '<dc:type>Registration</dc:type>'
            '<dc:identifier>https://doi.example/10.17605/OSF.IO/2C4ST</dc:identifier>'
            '<dc:identifier>https://osf.example/2c4st</dc:identifier>'
            '<dc:relation>https://osf.example/482n5</dc:relation>'
            '<dc:relation>https://osf.example/hnm67</dc:relation>'
            '<dc:rights>https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode</dc:rights>'
            '</oai_dc:dc>'
        ),
    }
