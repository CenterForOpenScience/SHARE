from providers.io.osf.harvester import OSFHarvester


class PreprintHarvester(OSFHarvester):
    PATH = 'v2/preprint_providers/osf/preprints/'
    EMBED_ATTRS = {
        'contributors': 'relationships.contributors.links.related.href',
    }
