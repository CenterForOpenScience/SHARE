import http
import inspect


class TroveError(Exception):
    # set more helpful codes in subclasses
    http_status: int = http.HTTPStatus.INTERNAL_SERVER_ERROR
    error_location: str = ''

    def __init__(self, *args):
        super().__init__(*args)
        self.error_location = _get_nearest_code_location()


###
# digesting metadata

class DigestiveError(TroveError):
    pass


class CannotDigestMediatype(DigestiveError):
    pass


class CannotDigestDateValue(DigestiveError):
    pass


class CannotDigestExpiredDatum(DigestiveError):
    pass


###
# parsing a request

class RequestParsingError(TroveError):
    http_status = http.HTTPStatus.BAD_REQUEST


class InvalidQuotedIri(RequestParsingError):
    pass


class InvalidQueryParamName(RequestParsingError):
    pass


class InvalidFilterOperator(InvalidQueryParamName):
    pass


class InvalidQueryParamValue(RequestParsingError):
    pass


class InvalidSearchText(InvalidQueryParamValue):
    pass


class MissingRequiredQueryParam(RequestParsingError):
    pass


class InvalidRepeatedQueryParam(RequestParsingError):
    pass


class InvalidPropertyPath(RequestParsingError):
    pass


class InvalidQueryParams(RequestParsingError):
    pass


###
# rendering a response

class ResponseRenderingError(TroveError):
    pass


class CannotRenderMediatype(ResponseRenderingError):
    http_status = http.HTTPStatus.NOT_ACCEPTABLE


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
# local helpers

def _get_nearest_code_location() -> str:
    try:
        _raise_frame = next(
            _frameinfo for _frameinfo in inspect.stack()
            if _frameinfo.filename != __file__  # nearest frame not in this file
        )
        return f'{_raise_frame.filename}::{_raise_frame.lineno}'
    except Exception:
        return 'unknown'  # eh, whatever
