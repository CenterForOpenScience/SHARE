from django.conf import settings
from django.http import HttpResponse

import sentry_sdk

from api.deprecation import get_view_func_deprecation_level, DeprecationLevel


class DeprecationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        deprecation_level = get_view_func_deprecation_level(view_func)

        if deprecation_level in (DeprecationLevel.LOGGED, DeprecationLevel.HIDDEN):
            sentry_sdk.capture_message('\n\t'.join((
                'Deprecated view usage:',
                f'request.path: {request.path}',
                f'request.method: {request.method}',
                f'deprecation_level: {deprecation_level}',
                f'HIDE_DEPRECATED_VIEWS: {settings.HIDE_DEPRECATED_VIEWS}',
            )))

        if settings.HIDE_DEPRECATED_VIEWS and deprecation_level == DeprecationLevel.HIDDEN:
            return HttpResponse(
                f'This path ({request.path}) has been removed. If you have built something that relies on it, please email us at share-support@osf.io',
                status=410,
            )

        return None  # continue processing as normal
