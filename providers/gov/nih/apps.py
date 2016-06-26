from share.provider import ProviderAppConfig
from .harvester import NIHHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.nih'
    title = 'nih'
    long_title = 'NIH Research Portal Online Reporting Tools'
    home_page = 'http://exporter.nih.gov/ExPORTER_Catalog.aspx/'
    harvester = NIHHarvester
