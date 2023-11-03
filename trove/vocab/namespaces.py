from primitive_metadata.primitive_rdf import (
    IriNamespace,
    IriShorthand,
    RDF,
    RDFS,
    OWL,
)


# established standards
# RDF: http://www.w3.org/1999/02/22-rdf-syntax-ns#
# RDFS: http://www.w3.org/2000/01/rdf-schema#
# OWL: http://www.w3.org/2002/07/owl#
DCTERMS = IriNamespace('http://purl.org/dc/terms/')
DC = IriNamespace('http://purl.org/dc/elements/1.1/')
DCMITYPE = IriNamespace('http://purl.org/dc/dcmitype/')
FOAF = IriNamespace('http://xmlns.com/foaf/0.1/')
DCAT = IriNamespace('http://www.w3.org/ns/dcat#')
PROV = IriNamespace('http://www.w3.org/ns/prov#')
OAI = IriNamespace('http://www.openarchives.org/OAI/2.0/')
OAI_DC = IriNamespace('http://www.openarchives.org/OAI/2.0/oai_dc/')
SKOS = IriNamespace('http://www.w3.org/2004/02/skos/core#')

# a new namespace for SHARE/trove concepts
TROVE = IriNamespace('https://share.osf.io/vocab/2023/trove/')
# a wild namespace for whatever lingers from SHAREv2
SHAREv2 = IriNamespace('https://share.osf.io/vocab/2017/sharev2/')
# for the OSF metadata application profile (TODO: update to resolvable URL, when there is one)
OSFMAP = IriNamespace('https://osf.io/vocab/2022/')

# for identifying jsonapi concepts with linked anchors on the jsonapi spec (probably fine)
JSONAPI = IriNamespace('https://jsonapi.org/format/1.1/#')


STATIC_SHORTHAND = IriShorthand({
    'rdf': RDF,
    'rdfs': RDFS,
    'owl': OWL,
    'dc': DC,
    'dcterms': DCTERMS,
    'dcmitype': DCMITYPE,
    'foaf': FOAF,
    'dcat': DCAT,
    'prov': PROV,
    'skos': SKOS,
    'trove': TROVE,
    'sharev2': SHAREv2,
    'osf': OSFMAP,
    'jsonapi': JSONAPI,
})
