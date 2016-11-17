from share.provider import ProviderAppConfig
from .harvester import SocarxivHarvester
# from providers.io.osf.preprints.normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.org.socarxiv'
    version = '0.0.1'
    title = 'osf_preprints_socarxiv'
    long_title = 'SocArXiv'
    emitted_type = 'preprint'
    home_page = 'https://socopen.org/'
    harvester = SocarxivHarvester
    # temporary change - switch back to PreprintNormalizer when preprint branding is complete
    # normalizer = PreprintNormalizer
