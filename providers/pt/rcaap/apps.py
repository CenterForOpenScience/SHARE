from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.pt.rcaap'
    version = '0.0.1'
    title = 'rcaap'
    long_title = 'RCAAP - Repositório Científico de Acesso Aberto de Portugal'
    home_page = 'http://www.rcaap.pt'
    url = 'http://www.rcaap.pt/oai'
    approved_sets = ['portugal']
    time_granularity = False
