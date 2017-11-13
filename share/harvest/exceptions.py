from share.exceptions import HarvestError


# TODO replace with a more generic ConcurrencyError
class HarvesterConcurrencyError(HarvestError):
    pass
