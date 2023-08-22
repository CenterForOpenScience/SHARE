from gather import primitive_rdf


# established standards
RDF = primitive_rdf.RDF  # http://www.w3.org/1999/02/22-rdf-syntax-ns#
RDFS = primitive_rdf.RDFS  # http://www.w3.org/2000/01/rdf-schema#
OWL = primitive_rdf.OWL  # http://www.w3.org/2002/07/owl#
DCTERMS = primitive_rdf.IriNamespace('http://purl.org/dc/terms/')
DCMITYPE = primitive_rdf.IriNamespace('http://purl.org/dc/dcmitype/')
FOAF = primitive_rdf.IriNamespace('http://xmlns.com/foaf/0.1/')
DCAT = primitive_rdf.IriNamespace('http://www.w3.org/ns/dcat#')
PROV = primitive_rdf.IriNamespace('http://www.w3.org/ns/prov#')
OAI = primitive_rdf.IriNamespace('http://www.openarchives.org/OAI/2.0/')
OAI_DC = primitive_rdf.IriNamespace('http://www.openarchives.org/OAI/2.0/oai_dc/')
SKOS = primitive_rdf.IriNamespace('http://www.w3.org/2004/02/skos/core#')

# a new namespace for SHARE/trove concepts
TROVE = primitive_rdf.IriNamespace('https://share.osf.io/vocab/2023/trove/')
# a wild namespace for whatever lingers from SHAREv2
SHAREv2 = primitive_rdf.IriNamespace('https://share.osf.io/vocab/2017/sharev2/')
# for the OSF metadata application profile (TODO: update to resolvable URL, when there is one)
OSFMAP = primitive_rdf.IriNamespace('https://osf.io/vocab/2022/')

# for identifying jsonapi concepts with linked anchors on the jsonapi spec (probably fine)
JSONAPI = primitive_rdf.IriNamespace('https://jsonapi.org/format/1.1/#')
