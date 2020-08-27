from io import StringIO
import cProfile
import pstats

from django.conf import settings
from django.http import HttpResponse

from raven.contrib.django.raven_compat.models import client as sentry_client

from api.deprecation import get_view_func_deprecation_level, DeprecationLevel


# Adapted from http://www.djangosnippets.org/snippets/186/
# Original author: udfalkso
# Modified by: Shwagroo Team and Gun.io
# Modified by: COS
class ProfileMiddleware:
    """
    Displays hotshot profiling for any view.
    http://yoursite.com/yourview/?prof
    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode, is available for superuser otherwise,
    but you really shouldn't add this middleware to any production configuration.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not ((settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET):
            return self.get_response(request)

        request.GET._mutable = True
        request.GET.pop('prof')
        request.GET._mutable = False

        prof = cProfile.Profile()
        prof.enable()

        response = self.get_response(request)

        prof.disable()

        s = StringIO()
        ps = pstats.Stats(prof, stream=s).sort_stats('cumtime')
        ps.print_stats()

        response.content = s.getvalue()

        return response


class DeprecationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        deprecation_level = get_view_func_deprecation_level(view_func)

        if deprecation_level in (DeprecationLevel.LOGGED, DeprecationLevel.HIDDEN):
            sentry_client.captureMessage('Deprecated view usage', data={
                'request': {
                    'path': request.path,
                    'method': request.method,
                },
                'deprecation_level': deprecation_level,
                'HIDE_DEPRECATED_VIEWS': settings.HIDE_DEPRECATED_VIEWS,
            })

        if settings.HIDE_DEPRECATED_VIEWS and deprecation_level == DeprecationLevel.HIDDEN:
            return HttpResponse(
                f'This path ({request.path}) has been removed. If you have built something that relies on it, please email us at share-support@osf.io',
                status=410,
            )

        return None  # continue processing as normal
