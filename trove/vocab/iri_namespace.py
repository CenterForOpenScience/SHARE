import gather


# established standards
RDF = gather.RDF  # http://www.w3.org/1999/02/22-rdf-syntax-ns#
RDFS = gather.RDFS  # http://www.w3.org/2000/01/rdf-schema#
OWL = gather.OWL  # http://www.w3.org/2002/07/owl#
DCTERMS = gather.IriNamespace('http://purl.org/dc/terms/')
FOAF = gather.IriNamespace('http://xmlns.com/foaf/0.1/')
DCAT = gather.IriNamespace('http://www.w3.org/ns/dcat#')
PROV = gather.IriNamespace('http://www.w3.org/ns/prov#')
OAI = gather.IriNamespace('http://www.openarchives.org/OAI/2.0/')
OAI_DC = gather.IriNamespace('http://www.openarchives.org/OAI/2.0/oai_dc/')

# a new namespace for SHARE/trove concepts
TROVE = gather.IriNamespace('https://share.osf.io/vocab/2023/trove/')
# a wild namespace for whatever lingers from SHAREv2
SHAREv2 = gather.IriNamespace('https://share.osf.io/vocab/2017/sharev2/')
# for the OSF metadata application profile
OSFMAP = gather.IriNamespace('https://osf.io/vocab/2022/')

# for identifying jsonapi concepts with linked anchors on the jsonapi spec (probably fine)
JSONAPI = gather.IriNamespace('https://jsonapi.org/format/1.1/#')
