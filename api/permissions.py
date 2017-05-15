import logging

from oauth2_provider.ext.rest_framework import TokenHasScope
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS


log = logging.getLogger(__name__)


class ReadOnlyOrTokenHasScopeOrIsAuthenticated(TokenHasScope, IsAuthenticated, BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if request.user and request.user.is_authenticated:
            return True

        token = request.auth

        if not token:
            return False

        if hasattr(token, 'scope'):  # OAuth 2
            required_scopes = self.get_scopes(request, view)
            log.debug("Required scopes to access resource: {0}".format(required_scopes))

            return token.is_valid(required_scopes)

        assert False, ('TokenHasScope requires either the'
                       '`oauth2_provider.rest_framework.OAuth2Authentication` authentication '
                       'class to be used.')


class IsDeletedPremissions(BasePermission):
    """
    Permission check for deleted objects.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'is_deleted') and obj.is_deleted:
                raise PermissionDenied('Query is forbidden for the given object.')
        return True
