from share.harvest.oai import OAIHarvester


class ArxivHarvester(OAIHarvester):
    time_granularity = False
    url = 'http://export.arxiv.org/oai2'
