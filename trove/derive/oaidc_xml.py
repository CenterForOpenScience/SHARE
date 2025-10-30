from typing import Any
from lxml import etree
from primitive_metadata import primitive_rdf as rdf

from share.oaipmh.util import ns, nsmap, SubEl

from trove.util.datetime import datetime_isoformat_z as format_datetime
from trove.vocab.namespaces import (
    DCTYPE,
    DCTERMS,
    FOAF,
    OAI_DC,
    OSFMAP,
    RDF,
    RDFS,
    SHAREv2,
    SKOS,
)

from ._base import IndexcardDeriver


DC_RELATION_PREDICATES = {
    DCTERMS.hasPart,
    DCTERMS.hasVersion,
    DCTERMS.isPartOf,
    DCTERMS.isVersionOf,
    DCTERMS.references,
    OSFMAP.hasAnalyticCodeResource,
    OSFMAP.hasDataResource,
    OSFMAP.hasMaterialsResource,
    OSFMAP.hasPapersResource,
    OSFMAP.hasPreregisteredAnalysisPlan,
    OSFMAP.hasPreregisteredStudyDesign,
    OSFMAP.hasRoot,
    OSFMAP.hasSupplementalResource,
    OSFMAP.isContainedBy,
    OSFMAP.isSupplementedBy,
    OSFMAP.supplements,
}


class OaiDcXmlDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        return str(OAI_DC)

    # abstract method from IndexcardDeriver
    @staticmethod
    def derived_datatype_iris() -> tuple[str]:
        return (RDF.XMLLiteral,)

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        _allowed_focustype_iris = {
            SHAREv2.CreativeWork,
            OSFMAP.Project,
            OSFMAP.ProjectComponent,
            OSFMAP.Registration,
            OSFMAP.RegistrationComponent,
            OSFMAP.Preprint,
        }
        _focustype_iris = self.q(RDF.type)
        return _allowed_focustype_iris.isdisjoint(_focustype_iris)

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self) -> Any:
        _dc_element = self._derive_card_as_xml()
        return etree.tostring(_dc_element, encoding='unicode')

    def _derive_card_as_xml(self) -> etree.Element:
        dc_element = etree.Element(
            ns('oai_dc', 'dc'),
            attrib={
                ns('xsi', 'schemaLocation'): f'{OAI_DC} http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
            },
            nsmap=nsmap('oai_dc', 'dc', 'xsi'),
        )
        for _title in self.q(DCTERMS.title):
            SubEl(dc_element, ns('dc', 'title'), _title)

        for _creator_name in self.q({DCTERMS.creator: {FOAF.name}}):
            SubEl(dc_element, ns('dc', 'creator'), _creator_name)
        _subject_paths = [
            DCTERMS.subject,  # may use literal subject names
            {DCTERMS.subject: {RDFS.label, SKOS.prefLabel, SKOS.altLabel}},  # or labeled subjects
        ]
        for _subject in self.q(_subject_paths):
            if isinstance(_subject, rdf.Literal):
                SubEl(dc_element, ns('dc', 'subject'), _subject)

        for _description in sorted(self.q(DCTERMS.description)):
            SubEl(dc_element, ns('dc', 'description'), _description)

        for _publisher_name in sorted(self.q({DCTERMS.publisher: FOAF.name})):
            SubEl(dc_element, ns('dc', 'publisher'), _publisher_name)

        for _contributor_name in self.q({DCTERMS.contributor: FOAF.name}):
            SubEl(dc_element, ns('dc', 'contributor'), _contributor_name)

        try:
            _date = next(self.q([
                DCTERMS.date,
                DCTERMS.datePublished,
                DCTERMS.modified,
                DCTERMS.created,
            ]))
        except StopIteration:  # no date
            pass
        else:
            SubEl(dc_element, ns('dc', 'date'), format_datetime(_date))

        for _type_iri in sorted(self.q(RDF.type)):
            for _type_namespace in (OSFMAP, DCTYPE, SHAREv2):
                if _type_iri in _type_namespace:
                    SubEl(
                        dc_element,
                        ns('dc', 'type'),
                        rdf.iri_minus_namespace(_type_iri, _type_namespace),
                    )

        for _identifier in sorted(self.q(DCTERMS.identifier)):
            SubEl(dc_element, ns('dc', 'identifier'), _identifier)

        for _language in sorted(self.q(DCTERMS.language)):
            SubEl(dc_element, ns('dc', 'language'), _language)

        for _related_iri in sorted(self.q(DC_RELATION_PREDICATES)):
            SubEl(dc_element, ns('dc', 'relation'), _related_iri)

        for _rights in sorted(self.q(DCTERMS.rights)):
            _value = (
                _rights
                if isinstance(_rights, (str, rdf.Literal))
                else next(self.q({DCTERMS.rights: DCTERMS.title}), None)
            )
            if _value:
                SubEl(dc_element, ns('dc', 'rights'), _value)

        return dc_element
