from enum import Enum, auto


class DeprecationLevel(Enum):
    LOGGED = auto()
    HIDDEN = auto()


DEPRECATION_LEVEL_ATTR = '_deprecation_level'


def deprecate(*, pls_hide):
    """decorator to mark views or viewsets as deprecated

    requests to deprecated views will be logged to sentry (see api.middleware.DeprecationMiddleware)

    pls_hide (required): if truthy, should respond `410 Gone` instead of executing the view at all
    """
    def _deprecate_decorator(view_or_viewset):
        deprecation_level = DeprecationLevel.HIDDEN if pls_hide else DeprecationLevel.LOGGED
        setattr(view_or_viewset, DEPRECATION_LEVEL_ATTR, deprecation_level)
        return view_or_viewset
    return _deprecate_decorator


def get_view_func_deprecation_level(view_func):
    deprecation_level = getattr(view_func, DEPRECATION_LEVEL_ATTR, None)
    if deprecation_level is None:
        # when using DRF ViewSets, the ViewSet class is at view_func.cls
        viewset_class = getattr(view_func, 'cls', None)
        deprecation_level = getattr(viewset_class, DEPRECATION_LEVEL_ATTR, None)
    return deprecation_level
