from share.provider import ProviderAppConfig
from .harvester import EngrxivHarvester
from providers.io.osf.preprints.normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.engrxiv'
    version = '0.0.1'
    title = 'osf_preprints_engrxiv'
    long_title = 'engrXiv'
    home_page = 'http://osf.io/api/v1/search/'
    emitted_type = 'preprint'
    harvester = EngrxivHarvester
    normalizer = PreprintNormalizer
