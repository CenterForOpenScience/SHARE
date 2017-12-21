from share.exceptions import HarvestError


# TODO replace with a more generic ConcurrencyError, or delete (SHARE-1026)
class HarvesterConcurrencyError(HarvestError):
    pass
