
class ShareException(Exception):
    pass


class HarvestError(ShareException):
    pass


class IngestError(ShareException):
    pass


class TransformError(IngestError):
    pass
