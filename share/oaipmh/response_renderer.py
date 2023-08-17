
from datetime import datetime
from lxml import etree

from django.urls import reverse

from share.oaipmh.util import format_datetime, SubEl, ns, nsmap


class OAIRenderer:
    def __init__(self, repository, request):
        self.repository = repository
        self.request = request
        self.kwargs = {}

    def identify(self, earliest_datestamp):
        identify = etree.Element(ns('oai', 'Identify'))
        SubEl(identify, ns('oai', 'repositoryName'), self.repository.NAME)
        SubEl(identify, ns('oai', 'baseURL'), self.request.build_absolute_uri(reverse('oai-pmh')))
        SubEl(identify, ns('oai', 'protocolVersion'), '2.0')
        if earliest_datestamp:
            SubEl(identify, ns('oai', 'earliestDatestamp'), format_datetime(earliest_datestamp))
        SubEl(identify, ns('oai', 'deletedRecord'), 'no')
        SubEl(identify, ns('oai', 'granularity'), self.repository.GRANULARITY)
        for email in self.repository.ADMIN_EMAILS:
            SubEl(identify, ns('oai', 'adminEmail'), email)

        description = SubEl(identify, ns('oai', 'description'))
        identifier = SubEl(
            description,
            ns('oai', 'oai-identifier'),
            attrib={
                ns('xsi', 'schemaLocation'): 'http://www.openarchives.org/OAI/2.0/oai-identifier http://www.openarchives.org/OAI/2.0/oai-identifier.xsd',
            },
            nsmap=nsmap('xsi', default='oai-identifier'),
        )
        SubEl(identifier, ns('oai-identifier', 'scheme'), 'oai')
        SubEl(identifier, ns('oai-identifier', 'repositoryIdentifier'), self.repository.REPOSITORY_IDENTIFIER)
        SubEl(identifier, ns('oai-identifier', 'delimiter'), self.repository.IDENTIFER_DELIMITER)
        SubEl(identifier, ns('oai-identifier', 'sampleIdentifier'), self.repository.sample_identifier())

        return self._render(identify)

    def listMetadataFormats(self, formats):
        list_formats = etree.Element(ns('oai', 'ListMetadataFormats'))
        for metadata_prefix, format_info in formats.items():
            metadata_format = SubEl(list_formats, ns('oai', 'metadataFormat'))
            SubEl(metadata_format, ns('oai', 'metadataPrefix'), metadata_prefix)
            SubEl(metadata_format, ns('oai', 'schema'), format_info['schema'])
            SubEl(metadata_format, ns('oai', 'metadataNamespace'), format_info['namespace'])
        return self._render(list_formats)

    def listSets(self, sets):
        list_sets = etree.Element(ns('oai', 'ListSets'))
        for spec, name in sets:
            set = SubEl(list_sets, ns('oai', 'set'))
            SubEl(set, ns('oai', 'setSpec'), spec)
            SubEl(set, ns('oai', 'setName'), name)
        return self._render(list_sets)

    def listIdentifiers(self, indexcards, next_token):
        list_identifiers = etree.Element(ns('oai', 'ListIdentifiers'))
        for _indexcard in indexcards:
            list_identifiers.append(self._header(_indexcard))
        SubEl(list_identifiers, ns('oai', 'resumptionToken'), next_token)
        return self._render(list_identifiers)

    def listRecords(self, indexcards, next_token):
        list_records = etree.Element(ns('oai', 'ListRecords'))
        for _indexcard in indexcards:
            list_records.append(self._record(_indexcard))
        SubEl(list_records, ns('oai', 'resumptionToken'), next_token)
        return self._render(list_records)

    def getRecord(self, indexcard):
        get_record = etree.Element(ns('oai', 'GetRecord'))
        get_record.append(self._record(indexcard))
        return self._render(get_record)

    def errors(self, errors):
        elements = []
        for error in errors:
            element = etree.Element(ns('oai', 'error'), code=error.code)
            element.text = error.description
            elements.append(element)
        return self._render(*elements)

    def _render(self, *elements):
        root = etree.Element(
            ns('oai', 'OAI-PMH'),
            attrib={
                ns('xsi', 'schemaLocation'): 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd',
            },
            nsmap=nsmap('xsi', default='oai'),
        )
        SubEl(root, ns('oai', 'responseDate'), format_datetime(datetime.now()))
        request = SubEl(root, ns('oai', 'request'), self.request.build_absolute_uri().rpartition('?')[0])
        verb = self.kwargs.pop('verb', None)
        if verb:
            request.set('verb', verb)
            for k, v in self.kwargs.items():
                request.set(k, v)

        for element in elements:
            root.append(element)

        return etree.tostring(root, encoding='utf-8', xml_declaration=True)

    def _header(self, indexcard):
        header = etree.Element(ns('oai', 'header'))
        SubEl(header, ns('oai', 'identifier'), self.repository.oai_identifier(indexcard))
        SubEl(header, ns('oai', 'datestamp'), format_datetime(indexcard.oai_datestamp)),
        SubEl(header, ns('oai', 'setSpec'), indexcard.source_record_suid.source_config.source.name)
        return header

    def _record(self, indexcard):
        _record_element = etree.Element(ns('oai', 'record'))
        _record_element.append(self._header(indexcard))
        _metadata = SubEl(_record_element, ns('oai', 'metadata'))
        _metadata.append(etree.fromstring(indexcard.oai_metadata))
        # TODO SHARE-730 Add <about><provenance><originDescription> elements
        return _record_element
