from share.provider import ProviderAppConfig
from .harvester import DailySSRNHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.dailyssrn'
    title = 'dailyssrn'
    long_title = 'Social Science Research Network'
    home_page = 'http://papers.ssrn.com/'
    harvester = DailySSRNHarvester
