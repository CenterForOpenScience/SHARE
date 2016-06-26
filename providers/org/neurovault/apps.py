from share.provider import ProviderAppConfig
from .harvester import NeuroVaultHarvester

class AppConfig(ProviderAppConfig):
    name = 'providers.org.neurovault'
    title = 'neurovault'
    long_title = 'NeuroVault.org'
    home_page = 'http://www.neurovault.org/'
    harvester = NeuroVaultHarvester
