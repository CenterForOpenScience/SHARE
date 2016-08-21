from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.uncg'
    version = '0.0.1'
    title = 'uncg'
    long_title = 'UNC-Greensboro'
    home_page = 'http://libres.uncg.edu/ir'
    url = 'http://libres.uncg.edu/ir/oai/oai.aspx'
    approved_sets = ['UNCG']
