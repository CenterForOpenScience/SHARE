from primitive_metadata import primitive_rdf as rdf
from primitive_metadata.namespaces import (
    RDF,
    RDFS,
    OWL,
    DCTERMS,
    DC,
    DCTYPE,
    FOAF,
    DCAT,
    PROV,
    SKOS,
    XSD,
    DEFAULT_SHORTHAND,
)

__all__ = (
    'DC',
    'DCAT',
    'DCTYPE',
    'DCTERMS',
    'FOAF',
    'JSONAPI',
    'OAI',
    'OAI_DC',
    'OSFMAP',
    'OWL',
    'PROV',
    'RDF',
    'RDFS',
    'SHAREv2',
    'SKOS',
    'TROVE',
    'XSD',
    'NAMESPACES_SHORTHAND',
)

# namespaces used in OAI-PMH
OAI = rdf.IriNamespace('http://www.openarchives.org/OAI/2.0/')
OAI_DC = rdf.IriNamespace('http://www.openarchives.org/OAI/2.0/oai_dc/')

# a new namespace for SHARE/trove concepts
TROVE = rdf.IriNamespace('https://share.osf.io/vocab/2023/trove/')
# a wild namespace for whatever lingers from SHAREv2
SHAREv2 = rdf.IriNamespace('https://share.osf.io/vocab/2017/sharev2/')
# for the OSF metadata application profile (TODO: update to resolvable URL, when there is one)
OSFMAP = rdf.IriNamespace('https://osf.io/vocab/2022/')

# for identifying jsonapi concepts with linked anchors on the jsonapi spec (probably fine)
JSONAPI = rdf.IriNamespace('https://jsonapi.org/format/1.1/#')


NAMESPACES_SHORTHAND = DEFAULT_SHORTHAND.with_update({
    'trove': TROVE,
    'sharev2': SHAREv2,
    'osf': OSFMAP,
    'jsonapi': JSONAPI,
    'oai': OAI,
    'oai_dc': OAI_DC,
})
