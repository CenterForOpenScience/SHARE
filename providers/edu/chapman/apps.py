from share.provider import OAIProviderAppConfig
from .harvester import ChapmanHarvester


class CaltechConfig(OAIProviderAppConfig):
    name = 'providers.edu.caltech'

    title = 'chapman'
    long_title = 'Chapman University Digital Commons'
    harvester = ChapmanHarvester
    home_page = 'http://digitalcommons.chapman.edu'
