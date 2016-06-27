from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.br.pcurio'
    title = 'pcurio'
    long_title = 'Pontifical Catholic University of Rio de Janeiro'
    home_page = 'http://www.maxwell.vrac.puc-rio.br'
    url = 'http://www.maxwell.vrac.puc-rio.br/DC_Todos.php'
    timezone_granularity = False
