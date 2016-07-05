from share.provider import ProviderAppConfig
from .harvester import OSFRegistrationsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.io.osf.registrations'
    version = '0.0.1'
    title = 'osf_registrations'
    long_title = 'Open Science Framework Registrations'
    home_page = 'http://api.osf.io/registrations/'
    harvester = OSFRegistrationsHarvester
