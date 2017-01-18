from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.info.ssoar'
    version = '0.0.1'
    title = 'ssoar'
    long_title = 'Social Science Open Access Repository'
    home_page = 'http://www.ssoar.info/en/home.html'
    url = 'http://www.ssoar.info/OAIHandler/request'
