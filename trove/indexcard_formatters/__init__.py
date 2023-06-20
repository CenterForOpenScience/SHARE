from . import (
    _base,
    sharev2_elastic,
    # osfmap_jsonld,
    # oai_dc_xml,
)


INDEXCARD_FORMATTER_CLASSES: list[type[_base.IndexcardFormatter]] = [
    sharev2_elastic.Sharev2ElasticFormatter,
    # TODO:
    # osfmap_jsonld...
    # oai_dc_xml...
]


INDEXCARD_FORMATTER_CLASS_BY_FORMAT_IRI: dict[str, type[_base.IndexcardFormatter]] = {
    _formatter_class.FORMAT_IRI: _formatter_class
    for _formatter_class in INDEXCARD_FORMATTER_CLASSES
    if _formatter_class.FORMAT_IRI is not None
}
