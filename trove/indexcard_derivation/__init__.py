from share.util.rdfutil import SHAREv2
from . import (
    sharev2_elastic,
    # osfmap_jsonld,
    # oai_dc_xml,
)


INDEXCARD_DERIVATION_BY_IRI = {
    SHAREv2.sharev2_elastic: sharev2_elastic.Sharev2ElasticDerivation,
    # TODO:
    # osfmap_jsonld...
    # oai_dc_xml...
}
