from . import (
    sharev2_elastic,
    osfmap_json,
    oaidc_xml,
)


DERIVER_SET = (
    sharev2_elastic.ShareV2ElasticDeriver,
    osfmap_json.OsfmapJsonDeriver,
    oaidc_xml.OaiDcXmlDeriver,
    # TODO:
    # datacite_xml, (from osf.metadata)
    # datacite_json, (from osf.metadata)
    # property_label?
    # osfmap_jsonld_minimal?
)


def get_deriver_classes(deriver_iri_filter=None):
    if deriver_iri_filter is None:
        return DERIVER_SET
    return [
        _deriver_class
        for _deriver_class in DERIVER_SET
        if _deriver_class.deriver_iri() in deriver_iri_filter
    ]
