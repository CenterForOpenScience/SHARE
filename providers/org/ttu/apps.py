from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.ttu'
    version = '0.0.1'
    title = 'ttu'
    long_title = 'Texas Tech Univeristy Libraries'
    home_page = 'http://ttu-ir.tdl.org/'
    url = 'http://ttu-ir.tdl.org/ttu-oai/request'
    time_granularity = False
    approved_sets = ['col_2346_521', 'col_2346_469']
