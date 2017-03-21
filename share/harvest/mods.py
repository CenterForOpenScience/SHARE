from .oai import OAIHarvester


class MODSHarvester(OAIHarvester):

    metadata_prefix = 'mods'
    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
        'mods': 'http://www.loc.gov/mods/v3'
    }
