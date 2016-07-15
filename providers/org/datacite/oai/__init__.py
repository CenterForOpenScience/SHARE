default_app_config = 'providers.org.datacite.oai.apps.AppConfig'

"""
Example Record Deleted

<record>
    <header status="deleted">
        <identifier>oai:oai.datacite.org:25469</identifier>
        <datestamp>2011-04-04T23:45:12Z</datestamp><
        setSpec>ANDS</setSpec><setSpec>ANDS.TEST</setSpec>
    </header>
</record>
"""

"""
Example Record

<record>
    <header>
        <identifier>oai:oai.datacite.org:32153</identifier>
        <datestamp>2011-06-08T08:57:11Z</datestamp>
        <setSpec>TIB</setSpec>
        <setSpec>TIB.WDCC</setSpec>
    </header>
    <metadata>
        <oai_datacite xmlns="http://schema.datacite.org/oai/oai-1.0/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://schema.datacite.org/oai/oai-1.0/
            oai_datacite.xsd">
                <isReferenceQuality>true</isReferenceQuality>
                <schemaVersion>2.1</schemaVersion>
                <datacentreSymbol>CISTI.JOE</datacentreSymbol>
                <payload>
                    <resource xmlns="http://datacite.org/schema/kernel-2.1"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://datacite.org/schema/kernel-2.1
                        http://schema.datacite.org/meta/kernel-2.1/metadata.xsd">
                            <identifier identifierType="DOI">10.5072/WDCC/CCSRNIES_SRES_B2</identifier>
                            <creators>
                                <creator>
                                    <creatorName>Toru, Nozawa</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Utor, Awazon</creatorName>
                                    <nameIdentifier nameIdentifierScheme="ISNI">1422 4586 3573 0476</nameIdentifier>
                                </creator>
                            </creators>
                            <titles>
                                <title>
                                    National Institute for Environmental Studies and Center for Climate System Research Japan
                                </title>
                                <title titleType="Subtitle">
                                    A survey
                                </title>
                            </titles>
                            <publisher>World Data Center for Climate (WDCC)</publisher>
                            <publicationYear>2004</publicationYear>
                            <subjects>
                                <subject>Earth sciences and geology</subject>
                                <subject subjectScheme="DDC">551 Geology, hydrology, meteorology</subject>
                            </subjects>
                            <contributors>
                                <contributor contributorType="DataManager">
                                    <contributorName>PANGAEA</contributorName>
                                </contributor>
                                <contributor contributorType="ContactPerson">
                                    <contributorName>Doe, John</contributorName>
                                    <nameIdentifier nameIdentifierScheme="ORCID">xyz789</nameIdentifier>
                                </contributor>
                            </contributors>
                            <dates>
                                <date dateType="Valid">2005-04-05</date>
                                <date dateType="Accepted">2005-01-01</date>
                            </dates>
                            <language>eng</language>
                            <resourceType resourceTypeGeneral="Image">Animation</resourceType>
                            <alternateIdentifiers>
                                <alternateIdentifier alternateIdentifierType="ISBN">937-0-1234-56789-X</alternateIdentifier>
                            </alternateIdentifiers>
                            <relatedIdentifiers>
                                <relatedIdentifier relatedIdentifierType="DOI" relationType="IsCitedBy">
                                    10.1234/testpub
                                </relatedIdentifier>
                                <relatedIdentifier relatedIdentifierType="URN" relationType="Cites">
                                    http://testing.ts/testpub
                                </relatedIdentifier>
                            </relatedIdentifiers>
                            <sizes>
                                <size>285 kb</size>
                                <size>100 pages</size>
                            </sizes>
                            <formats>
                                <format>text/plain</format>
                            </formats>
                            <version>1.0</version>
                            <rights>Open Database License [ODbL]</rights>
                            <descriptions>
                                <description descriptionType="Other">
                                    The current xml-example for a DataCite record is the official example from the documentation.
                                    <br/>
                                    Please look on datacite.org to find the newest versions of sample data and schemas.
                                </description>
                            </descriptions>
                    </resource>
                </payload>
        </oai_datacite>
    </metadata>
</record>
"""
