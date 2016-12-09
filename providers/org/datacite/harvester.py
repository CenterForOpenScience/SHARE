from share.harvest.oai import OAIHarvester


class DataciteHarvester(OAIHarvester):
    metadata_prefix = 'oai_datacite'
