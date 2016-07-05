from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.za.csir'
    version = '0.0.1'
    title = 'csir'
    long_title = 'CSIR Researchspace'
    home_page = 'http://researchspace.csir.co.za'
    url = 'http://researchspace.csir.co.za/oai/request'
    property_list = ['rights', 'format', 'source', 'date', 'identifier', 'type', 'setSpec']
