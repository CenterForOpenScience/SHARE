from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.calhoun'
    version = '0.0.1'
    title = 'calhoun'
    long_title = 'Calhoun: Institutional Archive of the Naval Postgraduate School'
    home_page = 'http://calhoun.nps.edu'
    url = 'http://calhoun.nps.edu/oai/request'
    approved_sets = ['com_10945_7075', 'com_10945_6', 'col_10945_17']
