from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.uk.lshtm'
    title = 'lshtm'
    long_title = 'London School of Hygiene and Tropical Medicine Research Online'
    home_page = 'http://researchonline.lshtm.ac.uk'
    url = 'http://researchonline.lshtm.ac.uk/cgi/oai2'
