from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.za.csir'
    title = 'csir'
    long_title = 'CSIR Researchspace'
    home_page = 'http://researchspace.csir.co.za'
    url = 'http://researchspace.csir.co.za/oai/request'
