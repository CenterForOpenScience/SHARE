from . import (
    sharev2_elastic,
)


INDEXCARD_DERIVERS = (
    sharev2_elastic.ShareV2ElasticDeriver,
    # TODO:
    # osfmap_jsonld,
    # oai_dc_xml,
    # datacite_xml, (from osf.metadata)
    # datacite_json, (from osf.metadata)
    # property_label?
    # osfmap_jsonld_minimal?
)


INDEXCARD_DERIVER_BY_IRI = {
    _deriver_class.deriver_iri(): _deriver_class
    for _deriver_class in INDEXCARD_DERIVERS
}
