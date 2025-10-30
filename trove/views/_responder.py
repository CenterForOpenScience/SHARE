import datetime
import re
import typing

from django import http as djhttp

from trove.render._base import BaseRenderer
from trove.render.rendering import ProtoRendering
from trove.render.rendering.streamable import StreamableRendering
from trove.render.rendering.html_wrapped import HtmlWrappedRendering
from trove.exceptions import TroveError
from trove.vocab import mediatypes


_BROWSER_FRIENDLY_MEDIATYPES = {
    mediatypes.HTML,
    mediatypes.JSON,
    mediatypes.JSONLD,
    mediatypes.JSONAPI,
    mediatypes.ATOM,
    mediatypes.RSS,
}


def make_http_response(
    *,
    content_rendering: ProtoRendering,
    http_headers: typing.Iterable[tuple[str, str]] = (),
    http_request: djhttp.HttpRequest | None = None,
) -> djhttp.HttpResponse | djhttp.StreamingHttpResponse:
    _response_type = (
        djhttp.StreamingHttpResponse
        if isinstance(content_rendering, StreamableRendering)
        else djhttp.HttpResponse
    )
    _download_filename = (
        http_request.GET.get('withFileName')
        if http_request is not None
        else None
    )
    if (
        _download_filename is None
        and content_rendering.mediatype not in _BROWSER_FRIENDLY_MEDIATYPES
        and http_request is not None
        and 'Accept' in http_request.headers
        and http_request.accepts(mediatypes.HTML)
    ):  # when browsing in browser, return html (unless given filename)
        content_rendering = HtmlWrappedRendering(content_rendering)
    _response = _response_type(
        content_rendering.iter_content(),
        content_type=_make_content_type(content_rendering.mediatype),
    )
    if _download_filename is not None:
        _file_name = _get_file_name(_download_filename, content_rendering.mediatype)
        _response.headers['Content-Disposition'] = _disposition(_file_name)
    return _response


def make_http_error_response(
    *,
    error: TroveError,
    renderer_type: type[BaseRenderer],
    http_headers: typing.Iterable[tuple[str, str]] = ()
) -> djhttp.HttpResponse:
    _content_rendering = renderer_type.render_error_document(error)
    return djhttp.HttpResponse(
        _content_rendering.iter_content(),
        status=error.http_status,
        content_type=_make_content_type(_content_rendering.mediatype),
    )


def _sanitize_file_name(requested_name: str) -> str:
    _underscored = re.sub(r'["\'/:\\;\s]', '_', requested_name)
    _datestamp = datetime.date.today().isoformat()
    return f'{_datestamp}_{_underscored}' if _underscored else _datestamp


def _get_file_name(requested_name: str, mediatype: str) -> str:
    _file_name = _sanitize_file_name(requested_name)
    _dot_extension = mediatypes.dot_extension(mediatype)
    if _file_name.endswith(_dot_extension):
        return _file_name
    return f'{_file_name}{_dot_extension}'


def _disposition(filename: str) -> bytes:
    return b'; '.join((
        b'attachment',
        b'filename=' + filename.encode('latin-1', errors='replace'),
        b"filename*=utf-8''" + filename.encode(),
    ))


def _make_content_type(mediatype: str) -> str:
    """make a content-type header value from a mediatype

    currently just adds "charset=utf-8" to text mediatypes that don't already have one
    """
    if mediatype.startswith('text/') and ('charset' not in mediatype):
        return f'{mediatype};charset=utf-8'
    return mediatype
