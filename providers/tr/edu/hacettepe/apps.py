from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.tr.edu.hacettepe'
    version = '0.0.1'
    title = 'hacettepe'
    long_title = 'Hacettepe University DSpace on LibLiveCD'
    home_page = 'http://bbytezarsivi.hacettepe.edu.tr'
    url = 'http://bbytezarsivi.hacettepe.edu.tr/oai/request'
    disabled = True  # Server just times out
