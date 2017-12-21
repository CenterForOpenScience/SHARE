class HarvestError(Exception):
    pass


class HarvesterConcurrencyError(HarvestError):
    pass


class HarvesterDisabledError(HarvestError):
    pass
