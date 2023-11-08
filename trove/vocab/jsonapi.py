from trove.vocab.namespaces import JSONAPI


# using linked anchors on the jsonapi spec as iris (probably fine)
JSONAPI_MEMBERNAME = JSONAPI['document-member-names']
JSONAPI_RELATIONSHIP = JSONAPI['document-resource-object-relationships']
JSONAPI_ATTRIBUTE = JSONAPI['document-resource-object-attributes']
JSONAPI_LINK = JSONAPI['document-links']
JSONAPI_LINK_OBJECT = JSONAPI['document-links-link-object']

JSONAPI_MEDIATYPE = 'application/vnd.api+json'
