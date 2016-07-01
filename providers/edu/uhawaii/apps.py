from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.uhawaii'
    version = '0.0.1'
    title = 'uhawaii'
    long_title = 'ScholarSpace at University of Hawaii at Manoa'
    home_page = 'https://scholarspace.manoa.hawaii.edu'
    url = 'https://scholarspace.manoa.hawaii.edu/dspace-oai/request'
