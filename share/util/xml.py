import re

# match characters not allowed in XML
RE_XML_ILLEGAL = re.compile(
    '([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])'
    + '|'
    + (
        '([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])'
        % (
            chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
            chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
            chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff)
        )
    )
)


def strip_illegal_xml_chars(string):
    return RE_XML_ILLEGAL.sub('', string)
