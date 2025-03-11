import datetime

from lxml import etree
from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import OAI, OAI_DC


def format_datetime(dt):
    """OAI-PMH has specific time format requirements -- comply.
    """
    if isinstance(dt, primitive_rdf.Literal):
        dt = dt.unicode_value
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


XML_NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'oai': str(OAI),
    'oai_dc': str(OAI_DC),
    'oai-identifier': 'http://www.openarchives.org/OAI/2.0/oai-identifier',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xml': 'http://www.w3.org/XML/1998/namespace',
}


def ns(namespace_prefix, tag_name):
    """format XML tag/attribute name with full namespace URI

    see https://lxml.de/tutorial.html#namespaces
    """
    return f'{{{XML_NAMESPACES[namespace_prefix]}}}{tag_name}'


def nsmap(*namespace_prefixes, default=None):
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
def SubEl(parent, tag_name, text=None, **kwargs):
    element = etree.SubElement(parent, tag_name, **kwargs)
    if isinstance(text, primitive_rdf.Literal):
        _language_tag = text.language
        if _language_tag:
            element.set(ns('xml', 'lang'), text.language)
        element.text = text.unicode_value
    elif text:
        element.text = text
    return element
