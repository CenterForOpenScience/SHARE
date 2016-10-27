from share.provider import ProviderAppConfig
from .harvester import PhilicaHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.philica'
    version = '0.0.1'
    title = 'philica'
    long_title = 'Philica'
    home_page = 'http://philica.com/'
    harvester = PhilicaHarvester
    emitted_type = 'preprint'
