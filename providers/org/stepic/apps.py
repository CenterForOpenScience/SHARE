from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.stepic'
    version = '0.0.1'
    title = 'stepic'
    long_title = 'Stepic.org Online Education Platform'
    home_page = 'http://www.stepic.org'
    url = 'https://stepic.org/api/lessons'
    disabled = True  # Endpoint does not return OAI data. Also only a list of classes
