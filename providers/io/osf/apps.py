from share.provider import ProviderAppConfig
from .harvester import OSFHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.io.osf'
    title = 'osf'
    long_title = 'Open Science Framework'
    home_page = 'http://osf.io/api/v1/search/'
    harvester = OSFHarvester
