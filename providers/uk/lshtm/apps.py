from share.provider import OAIProviderAppConfig
from .normalizer import LSHTMNormalizer


class AppConfig(OAIProviderAppConfig):
    name = 'providers.uk.lshtm'
    version = '0.0.1'
    title = 'lshtm'
    long_title = 'London School of Hygiene and Tropical Medicine Research Online'
    home_page = 'http://researchonline.lshtm.ac.uk'
    url = 'http://researchonline.lshtm.ac.uk/cgi/oai2'
    normalizer = LSHTMNormalizer
