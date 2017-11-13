from share.exceptions import TransformError


class InvalidDate(TransformError):
    pass


class NoneOf(TransformError):
    """All of a OneOfLink's chains failed
    """
    pass


class InvalidIRI(TransformError):
    pass


class InvalidPath(TransformError):
    pass


class InvalidText(TransformError):
    pass
