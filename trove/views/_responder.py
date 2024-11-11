import typing

from django import http as djhttp

from trove.render._base import BaseRenderer
from trove.render._rendering import ProtoRendering
from trove.exceptions import TroveError


def make_http_response(
    *,
    content_rendering: ProtoRendering,
    http_headers: typing.Iterable[tuple[str, str]] = ()
) -> djhttp.HttpResponse:
    _response_cls = (
        djhttp.HttpResponse
        if content_rendering.is_streamed
        else djhttp.StreamingHttpResponse
    )
    return _response_cls(
        content_rendering.iter_content(),
        content_type=content_rendering.mediatype,
    )


def make_http_error_response(
    *,
    error: TroveError,
    renderer: BaseRenderer,
    http_headers: typing.Iterable[tuple[str, str]] = ()
) -> djhttp.HttpResponse:
    _content_rendering = renderer.render_error_document(error)
    return djhttp.HttpResponse(
        _content_rendering.iter_content(),
        status=error.http_status,
        content_type=_content_rendering.mediatype,
    )
