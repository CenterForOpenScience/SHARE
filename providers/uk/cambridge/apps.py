from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.uk.cambridge'
    version = '0.0.1'
    title = 'cambridge'
    long_title = 'Apollo @ University of Cambridge'
    home_page = 'https://www.repository.cam.ac.uk'
    url = 'https://www.repository.cam.ac.uk/oai/request'
    property_list = ['date', 'identifier', 'type', 'format', 'setSpec']
