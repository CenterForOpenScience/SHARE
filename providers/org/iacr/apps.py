from share.provider import ProviderAppConfig
from .harvester import IACRHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.iacr'
    version = '0.0.1'
    title = 'iacr'
    long_title = 'Cryptology ePrint Archive'
    home_page = 'https://eprint.iacr.org/'
    harvester = IACRHarvester
    emitted_type = 'preprint'

