from io import StringIO
import cProfile
import pstats

from django.conf import settings


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
