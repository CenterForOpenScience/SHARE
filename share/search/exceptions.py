from share.exceptions import ShareException


class DaemonSetupError(ShareException):
    pass


class DaemonMessageError(ShareException):
    pass


class DaemonIndexingError(ShareException):
    pass


class IndexStrategyError(ShareException):
    pass
