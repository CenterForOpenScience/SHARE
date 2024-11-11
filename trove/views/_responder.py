import typing

from django import http as djhttp

from trove.render._rendering import ProtoRendering


def make_response(
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
