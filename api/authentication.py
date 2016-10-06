from rest_framework.authentication import SessionAuthentication
from oauth2_provider.ext.rest_framework import OAuth2Authentication


class NonCSRFSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the session-based user from the underlying HttpRequest object
        user = getattr(request._request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        # self.enforce_csrf(request)

        # CSRF passed with authenticated user
        return (user, None)


class APIV1TokenBackPortAuthentication(OAuth2Authentication):

    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        if token and isinstance(token, str):
            request.META['HTTP_AUTHORIZATION'] = token.replace('Token', 'Bearer')
        return super().authenticate(request)
