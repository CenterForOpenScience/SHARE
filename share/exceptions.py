
class ShareException(Exception):
    pass


class HarvestError(ShareException):
    pass


class IngestError(ShareException):
    pass


class TransformError(IngestError):
    pass


class RegulateError(IngestError):
    pass


class MergeRequired(IngestError):
    """A node disambiguated to multiple objects in the database.
    """
    pass


class IngestConflict(IngestError):
    """Multiple data being ingested at the same time conflicted.
    """
    pass


class BadPid(IngestError):
    pass
