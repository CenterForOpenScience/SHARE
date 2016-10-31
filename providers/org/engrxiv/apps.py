from share.provider import ProviderAppConfig
from .harvester import EngrxivHarvester
# from providers.io.osf.preprints.normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.org.engrxiv'
    version = '0.0.1'
    title = 'osf_preprints_engrxiv'
    long_title = 'engrXiv'
    home_page = 'http://engrxiv.org'
    emitted_type = 'preprint'
    harvester = EngrxivHarvester
    # temporary change - switch back to PreprintNormalizer when preprint branding is complete
    # normalizer = PreprintNormalizer
