from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.uk.lshtm'
    version = '0.0.1'
    title = 'lshtm'
    long_title = 'London School of Hygiene and Tropical Medicine Research Online'
    home_page = 'http://researchonline.lshtm.ac.uk'
    url = 'http://researchonline.lshtm.ac.uk/cgi/oai2'
    property_list = ['date', 'type', 'identifier', 'relation', 'setSpec']
