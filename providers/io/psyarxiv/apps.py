from share.provider import ProviderAppConfig
from .harvester import PsyarxivHarvester
# from providers.io.osf.preprints.normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.psyarxiv'
    version = '0.0.1'
    title = 'osf_preprints_psyarxiv'
    long_title = 'PsyArXiv'
    home_page = 'http://psyarxiv.org'
    emitted_type = 'preprint'
    harvester = PsyarxivHarvester
    # temporary change - switch back to PreprintNormalizer when preprint branding is complete
    # normalizer = PreprintNormalizer
