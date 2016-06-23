from share.provider import OAIProviderAppConfig
from .harvester import CaltechHarvester


class CaltechConfig(OAIProviderAppConfig):
    name = 'providers.edu.caltech'

    title = 'caltech'
    long_title = 'CaltechAUTHORS'
    harvester = CaltechHarvester
    home_page = 'http://authors.library.caltech.edu/'
