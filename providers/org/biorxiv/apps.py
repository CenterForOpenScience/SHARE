from share.provider import ProviderAppConfig
from .harvester import BiorxivHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.biorxiv'
    version = '0.0.0'
    title = 'biorxiv'
    long_title = 'BioRxiv'
    home_page = 'http://biorxiv.org/'
    rate_limit = (1, 3)
    url = 'http://connect.biorxiv.org/biorxiv_xml.php?subject=all'
    time_granularity = False
    harvester = BiorxivHarvester
