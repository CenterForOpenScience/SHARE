class TroveError(Exception):
    pass


###
# digesting metadata

class DigestiveError(TroveError):
    pass


class CannotDigestMediatype(DigestiveError):
    pass


###
# parsing a request

class RequestParsingError(TroveError):
    pass


class InvalidQuotedIri(RequestParsingError):
    pass


class InvalidQueryParamName(RequestParsingError):
    pass


class InvalidDate(RequestParsingError):
    pass


###
# primitive rdf

class PrimitiveRdfWhoopsy(TroveError):
    pass


class IriInvalid(PrimitiveRdfWhoopsy):
    pass


class IriMismatch(PrimitiveRdfWhoopsy):
    pass


class UnsupportedRdfType(PrimitiveRdfWhoopsy):
    pass


class MissingRdfType(PrimitiveRdfWhoopsy):
    pass


class UnsupportedRdfObject(PrimitiveRdfWhoopsy):
    pass


class ExpectedIriOrBlanknode(UnsupportedRdfObject):
    pass


class ExpectedLiteralObject(UnsupportedRdfObject):
    pass


class OwlObjection(PrimitiveRdfWhoopsy):
    pass


###
# rendering a response
