from typing import Any

from lxml import etree
from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import OAI, OAI_DC


XML_NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'oai': str(OAI),
    'oai_dc': str(OAI_DC),
    'oai-identifier': 'http://www.openarchives.org/OAI/2.0/oai-identifier',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xml': 'http://www.w3.org/XML/1998/namespace',
}


def ns(namespace_prefix: str, tag_name: str) -> str:
    """format XML tag/attribute name with full namespace URI

    see https://lxml.de/tutorial.html#namespaces
    """
    return f'{{{XML_NAMESPACES[namespace_prefix]}}}{tag_name}'


def nsmap(*namespace_prefixes: str, default: str | None = None) -> dict[str | None, str]:
    """build a namespace map suitable for lxml

    see https://lxml.de/tutorial.html#namespaces
    """
    return {
        (None if (prefix == default) else prefix): uri
        for prefix, uri in XML_NAMESPACES.items()
        if (
            prefix in namespace_prefixes
            or prefix == default
        )
    }


# wrapper for lxml.etree.SubElement, adds `text` kwarg for convenience
def SubEl(parent: etree.Element, tag_name: str, text: str | None = None, **kwargs: Any) -> etree.SubElement:
    element = etree.SubElement(parent, tag_name, **kwargs)
    if isinstance(text, primitive_rdf.Literal):
        _language_tag = text.language
        if _language_tag:
            element.set(ns('xml', 'lang'), text.language)
        element.text = text.unicode_value
    elif text:
        element.text = text
    return element
