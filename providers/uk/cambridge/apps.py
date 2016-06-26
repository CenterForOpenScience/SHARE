from share.provider import OAIProviderAppConfig


class CambridgeConfig(OAIProviderAppConfig):
    name = 'providers.uk.cambridge'
    title = 'cambridge'
    long_title = 'Apollo @ University of Cambridge'
    home_page = 'https://www.repository.cam.ac.uk'
    url = 'https://www.repository.cam.ac.uk/oai/request'
