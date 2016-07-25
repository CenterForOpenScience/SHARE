from share.provider import OAIProviderAppConfig

from providers.br.pcurio.normalizer import Normalizer


class AppConfig(OAIProviderAppConfig):
    name = 'providers.br.pcurio'
    version = '0.0.1'
    title = 'pcurio'
    long_title = 'Pontifical Catholic University of Rio de Janeiro'
    home_page = 'http://www.maxwell.vrac.puc-rio.br'
    url = 'http://www.maxwell.vrac.puc-rio.br/DC_Todos.php'
    time_granularity = False
    normalizer = Normalizer
