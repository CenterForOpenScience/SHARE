from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.calhoun'
    title = 'calhoun'
    long_title = 'Calhoun: Institutional Archive of the Naval Postgraduate School'
    home_page = 'http://calhoun.nps.edu'
    url = 'http://calhoun.nps.edu/oai/request'
