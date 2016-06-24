from share.harvest.harvester import OAIHarvester


class ArxivHarvester(OAIHarvester):
    rate_limit = (1, 3)
    time_granularity = False
    url = 'http://export.arxiv.org/oai2'
