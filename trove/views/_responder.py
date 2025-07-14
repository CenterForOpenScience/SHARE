import datetime
import re
import typing

from django import http as djhttp

from trove.render._base import BaseRenderer
from trove.render._rendering import (
    ProtoRendering,
    StreamableRendering,
)
from trove.exceptions import TroveError
from trove.vocab import mediatypes


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
    _response = _response_type(
        content_rendering.iter_content(),
        content_type=content_rendering.mediatype,
    )
    if http_request is not None:
        _requested_filename = http_request.GET.get('withFileName')
        if _requested_filename is not None:
            _file_name = _get_file_name(_requested_filename, content_rendering.mediatype)
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
        content_type=_content_rendering.mediatype,
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
