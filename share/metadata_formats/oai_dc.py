from lxml import etree
import rdflib

from share.oaipmh.util import format_datetime, ns, nsmap, SubEl
from share.metadata_formats.base import MetadataFormatter
from share.util import rdfutil


class OaiDcFormatter(MetadataFormatter):
    """builds an XML fragment in dublin core format, meant to be included within the
    <metadata> element of an OAI-PMH `listRecords` or `showRecord` response

    see https://www.openarchives.org/OAI/openarchivesprotocol.html for more details
    """

    def format(self, normalized_datum):
        rdfgraph = normalized_datum.get_rdfgraph()
        if not rdfgraph:
            return None
        suid = normalized_datum.raw.suid
        focus = rdfutil.normalize_pid_uri(suid.described_resource_pid)
        if not rdfutil.is_creativework(rdfgraph, focus):
            return None

        dc_formatted = self.build_dublin_core(rdfgraph, focus)
        return etree.tostring(dc_formatted, encoding='unicode')

    def build_dublin_core(self, rdfgraph, focus):
        dc_element = etree.Element(
            ns('oai_dc', 'dc'),
            attrib={
                ns('xsi', 'schemaLocation'): 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
            },
            nsmap=nsmap('oai_dc', 'dc', 'xsi'),
        )
        SubEl(dc_element, ns('dc', 'title'), rdfgraph.value(focus, rdfutil.DCT.title))

        creator_names = rdfutil.get_related_agent_names(rdfgraph, focus, {rdfutil.DCT.creator})
        for creator_name in creator_names:
            SubEl(dc_element, ns('dc', 'creator'), creator_name)

        subject_names = rdfgraph.objects(focus, rdfutil.DCT.subject)
        for subject_name in sorted(subject_names):
            SubEl(dc_element, ns('dc', 'subject'), subject_name)

        description = rdfgraph.value(focus, rdfutil.DCT.description)
        if description:
            SubEl(dc_element, ns('dc', 'description'), description)

        publisher_names = rdfutil.get_related_agent_names(rdfgraph, focus, {rdfutil.DCT.publisher})
        for publisher_name in sorted(publisher_names):
            SubEl(dc_element, ns('dc', 'publisher'), publisher_name)

        contributor_names = rdfutil.get_related_agent_names(rdfgraph, focus, {
            rdfutil.DCT.contributor,
            rdfutil.SHAREV2.PrincipalInvestigator,
            rdfutil.SHAREV2.PrincipalInvestigatorContact,
        })
        for contributor_name in sorted(contributor_names):
            SubEl(dc_element, ns('dc', 'contributor'), contributor_name)

        date = (
            rdfgraph.value(focus, rdfutil.DCT.available)
            or rdfgraph.value(focus, rdfutil.DCT.modified)
        )
        if date:
            SubEl(dc_element, ns('dc', 'date'), format_datetime(date))

        SubEl(dc_element, ns('dc', 'type'), rdfgraph.value(focus, rdflib.RDF.type))

        identifier_uris = rdfgraph.objects(focus, rdfutil.DCT.identifier)
        for identifier_uri in sorted(identifier_uris):
            SubEl(dc_element, ns('dc', 'identifier'), identifier_uri)

        language = rdfgraph.value(focus, rdfutil.DCT.language)
        if language:
            SubEl(dc_element, ns('dc', 'language'), language)

        for related_uri in self._get_related_uris(work_node):
            SubEl(dc_element, ns('dc', 'relation'), related_uri)

        rights = rdfgraph.value(focus, rdfutil.DCT.rights)
        if rights:
            SubEl(dc_element, ns('dc', 'rights'), rights)

        free_to_read_type = rdfgraph.value(focus, rdfutil.DCT.free_to_read_type)
        if free_to_read_type:
            SubEl(dc_element, ns('dc', 'rights'), free_to_read_type)

        return dc_element

    def _get_related_uris(self, work_node):
        related_work_uris = set()
        for related_work_node in work_node['related_works']:
            related_work_uris.update(
                identifier['uri']
                for identifier in related_work_node['identifiers']
            )
        return sorted(related_work_uris)
