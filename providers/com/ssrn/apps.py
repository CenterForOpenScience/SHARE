from share.provider import ProviderAppConfig
from .harvester import SSRNHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.ssrn'
    version = '0.0.1'
    title = 'ssrn'
    long_title = 'Social Science Research Network'
    home_page = 'http://papers.ssrn.com/'
    harvester = SSRNHarvester
