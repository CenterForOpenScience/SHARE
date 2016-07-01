from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.scholarscompass_vcu'
    version = '0.0.1'
    title = 'scholarscompass_vcu'
    long_title = 'VCU Scholars Compass'
    home_page = 'http://scholarscompass.vcu.edu'
    url = 'http://scholarscompass.vcu.edu/do/oai/'
