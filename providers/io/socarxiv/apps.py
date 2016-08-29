from share.provider import ProviderAppConfig
from .harvester import SocarxivHarvester
from providers.io.osf.preprints.normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.socarxiv'
    version = '0.0.1'
    title = 'osf_preprints_socarxiv'
    long_title = 'SocArXiv'
    emitted_type = 'preprint'
    home_page = 'http://osf.io/api/v1/search/'
    harvester = SocarxivHarvester
    normalizer = PreprintNormalizer
