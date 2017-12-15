class HarvestError(Exception):
    pass


# TODO replace with a more generic ConcurrencyError
class HarvesterConcurrencyError(HarvestError):
    pass
