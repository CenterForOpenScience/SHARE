from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.nku'
    version = '0.0.1'
    title = 'nku'
    long_title = 'NKU Institutional Repository'
    home_page = 'https://dspace.nku.edu'
    url = 'https://dspace.nku.edu/oai/request'
    approved_sets = ['com_11216_7', 'com_11216_20', 'col_11216_168']
    property_list = ['date', 'type', 'identifier', 'setSpec', 'publisher', 'language', 'relation']
