from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.uiucideals'
    version = '0.0.1'
    title = 'uiucideals'
    long_title = 'University of Illinois at Urbana-Champaign, IDEALS'
    home_page = 'https://www.ideals.illinois.edu'
    url = 'http://ideals.uiuc.edu/dspace-oai/request'
