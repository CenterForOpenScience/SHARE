from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.fr.archives-ouvertes.hal'
    version = '0.0.1'
    title = 'HAL'
    long_title = 'Hyper Articles en Ligne'
    home_page = 'https://hal.archives-ouvertes.fr/'
    url = 'https://api.archives-ouvertes.fr/oai/hal/'
    time_granularity = False
    emitted_type = 'article'
