from datetime import datetime
from io import StringIO
from xml.etree.ElementTree import ElementTree, Element, SubElement

from django.urls import reverse

from share.models import Contributor
from share.oaipmh.util import format_datetime


# For convenience
def SubEl(parent, tag, text=None, attrib={}):
    element = SubElement(parent, tag, attrib)
    if text:
        element.text = text
    return element


class OAIRenderer:
    def __init__(self, repository, request):
        self.repository = repository
        self.request = request
        self.kwargs = {}

    def identify(self, earliest_datestamp):
        identify = Element('Identify')
        SubEl(identify, 'repositoryName', self.repository.NAME)
        SubEl(identify, 'baseURL', self.request.build_absolute_uri(reverse('oai-pmh')))
        SubEl(identify, 'protocolVersion', '2.0')
        if earliest_datestamp:
            SubEl(identify, 'earliestDatestamp', format_datetime(earliest_datestamp))
        SubEl(identify, 'deletedRecord', 'no')
        SubEl(identify, 'granularity', self.repository.GRANULARITY)
        for email in self.repository.ADMIN_EMAILS:
            SubEl(identify, 'adminEmail', email)

        identifier = SubEl(SubEl(identify, 'description'), 'oai-identifier', attrib={
            'xmlns': 'http://www.openarchives.org/OAI/2.0/oai-identifier',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai-identifier http://www.openarchives.org/OAI/2.0/oai-identifier.xsd',
        })
        SubEl(identifier, 'scheme', 'oai')
        SubEl(identifier, 'repositoryIdentifier', self.repository.REPOSITORY_IDENTIFIER)
        SubEl(identifier, 'delimiter', self.repository.IDENTIFER_DELIMITER)
        SubEl(identifier, 'sampleIdentifier', self.repository.oai_identifier(1))

        return self._render(identify)

    def listMetadataFormats(self, formats):
        list_formats = Element('ListMetadataFormats')
        for prefix, renderer in formats.items():
            format = SubEl(list_formats, 'metadataFormat')
            SubEl(format, 'metadataPrefix', prefix)
            SubEl(format, 'schema', renderer.schema)
            SubEl(format, 'metadataNamespace', renderer.namespace)
        return self._render(list_formats)

    def listSets(self, sets):
        list_sets = Element('ListSets')
        for spec, name in sets:
            set = SubEl(list_sets, 'set')
            SubEl(set, 'setSpec', spec)
            SubEl(set, 'setName', name)
        return self._render(list_sets)

    def listIdentifiers(self, works, next_token):
        list_identifiers = Element('ListIdentifiers')
        for work in works:
            list_identifiers.append(self._header(work))
        SubEl(list_identifiers, 'resumptionToken', next_token)
        return self._render(list_identifiers)

    def listRecords(self, works, next_token, metadataRenderer):
        list_records = Element('ListRecords')
        for work in works:
            list_records.append(self._record(work, metadataRenderer))
        SubEl(list_records, 'resumptionToken', next_token)
        return self._render(list_records)

    def getRecord(self, work, metadataRenderer):
        get_record = Element('GetRecord')
        get_record.append(self._record(work, metadataRenderer))
        return self._render(get_record)

    def errors(self, errors):
        elements = []
        for error in errors:
            element = Element('error', code=error.code)
            element.text = error.description
            elements.append(element)
        return self._render(*elements)

    def _render(self, *elements):
        root = Element('OAI-PMH', {
            'xmlns': 'http://www.openarchives.org/OAI/2.0/',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
        })
        SubEl(root, 'responseDate', format_datetime(datetime.now()))
        request = SubEl(root, 'request', self.request.build_absolute_uri().rpartition('?')[0])
        verb = self.kwargs.pop('verb', None)
        if verb:
            request.set('verb', verb)
            for k, v in self.kwargs.items():
                request.set(k, v)

        for element in elements:
            root.append(element)
        with StringIO() as stream:
            ElementTree(root).write(stream, encoding='unicode', xml_declaration=True)
            return stream.getvalue()

    def _header(self, work):
        header = Element('header')
        SubEl(header, 'identifier', self.repository.oai_identifier(work))
        SubEl(header, 'datestamp', format_datetime(work.date_modified)),
        for spec in work.sources.all():
            SubEl(header, 'setSpec', spec.source.name)
        return header

    def _record(self, work, metadataRenderer):
        record = Element('record')
        record.append(self._header(work))
        metadata = SubEl(record, 'metadata')
        metadataRenderer.render_metadata(metadata, work)
        # TODO SHARE-730 Add <about><provenance><originDescription> elements
        return record


class MetadataRenderer:
    def __init__(self, repository):
        self.repository = repository

    @property
    def prefix(self):
        raise NotImplementedError()

    @property
    def schema(self):
        raise NotImplementedError()

    @property
    def namespace(self):
        raise NotImplementedError()

    def render_metadata(self, parent, work):
        raise NotImplementedError()


class DublinCoreRenderer(MetadataRenderer):
    schema = 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
    namespace = 'http://www.openarchives.org/OAI/2.0/oai_dc/'

    contributor_types = set(Contributor.get_types()) - set(['share.creator'])

    def render_metadata(self, parent, work):
        dc = SubEl(parent, 'oai_dc:dc', attrib={
            'xmlns:oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
        })
        if work.title:
            SubEl(dc, 'dc:title', work.title)

        agent_relation_types = ['share.creator', 'share.publisher'] + list(self.contributor_types)
        agent_relations = {k: [] for k in agent_relation_types}

        for relation in work.agent_relations.all():
            if relation.type not in agent_relations:
                continue
            agent_relations[relation.type].append(relation)

        for relation in sorted(agent_relations['share.creator'], key=lambda x: x.order_cited or -1):
            SubEl(dc, 'dc:creator', relation.cited_as or relation.agent.name)

        for subject in work.subjects.all():
            SubEl(dc, 'dc:subject', subject.name)

        if work.description:
            SubEl(dc, 'dc:description', work.description)

        for relation in agent_relations['share.publisher']:
            SubEl(dc, 'dc:publisher', relation.cited_as or relation.agent.name)

        for relation in sorted([relation for type_ in self.contributor_types for relation in agent_relations[type_]], key=lambda x: x.order_cited or -1):
            SubEl(dc, 'dc:contributor', relation.cited_as or relation.agent.name)

        date = work.date_published or work.date_updated
        if date:
            SubEl(dc, 'dc:date', format_datetime(date))

        SubEl(dc, 'dc:type', work._meta.model_name)

        for identifier in work.identifiers.all():
            SubEl(dc, 'dc:identifier', identifier.uri)

        if work.language:
            SubEl(dc, 'dc:language', work.language)

        for relation in work.incoming_creative_work_relations.all():
            if work.id == relation.subject_id:
                SubEl(dc, 'dc:relation', self.repository.oai_identifier(relation.related_id))
            else:
                SubEl(dc, 'dc:relation', self.repository.oai_identifier(relation.subject_id))

        if work.rights:
            SubEl(dc, 'dc:rights', work.rights)

        if work.free_to_read_type:
            SubEl(dc, 'dc:rights', work.free_to_read_type)
