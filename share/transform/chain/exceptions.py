from share.exceptions import TransformError


class ChainError(TransformError):
    def __init__(self, *args, **kwargs):
        self._chainStack = []
        super().__init__(self._chainStack, *args, **kwargs)

    def push(self, description):
        self._chainStack.append(description)


class InvalidDate(ChainError):
    pass


class NoneOf(ChainError):
    """All of a OneOfLink's chains failed
    """
    pass


class InvalidIRI(ChainError):
    pass


class InvalidPath(ChainError):
    pass


class InvalidText(ChainError):
    pass
