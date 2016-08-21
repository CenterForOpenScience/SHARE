from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.info.spdataverse'
    version = '0.0.1'
    title = 'spdataverse'
    long_title = 'Scholars Portal dataverse'
    home_page = 'http://dataverse.scholarsportal.info/dvn/'
    url = 'http://dataverse.scholarsportal.info/dvn/OAIHandler'
