from share.provider import ProviderAppConfig
from .harvester import DailySSRNHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.dailyssrn'
    version = '0.0.1'
    title = 'dailyssrn'
    long_title = 'Social Science Research Network'
    home_page = 'http://papers.ssrn.com/'
    harvester = DailySSRNHarvester
    disabled = True  # Disabled as no articles have been release in a while
