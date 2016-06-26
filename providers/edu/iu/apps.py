from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.iu'
    title = 'iu'
    long_title = 'Indiana University Libraries\' IUScholarWorks'
    home_page = 'https://scholarworks.iu.edu'
    url = 'https://scholarworks.iu.edu/dspace-oai/request'
