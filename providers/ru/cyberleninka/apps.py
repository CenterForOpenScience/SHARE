from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ru.cyberleninka'
    title = 'cyberleninka'
    long_title = 'CyberLeninka - Russian open access scientific library'
    home_page = 'http://cyberleninka.ru/'
    url = 'http://cyberleninka.ru/oai'
