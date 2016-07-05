from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.csuohio'
    version = '0.0.1'
    title = 'csuohio'
    long_title = 'Cleveland State University\'s EngagedScholarship@CSU'
    home_page = 'http://engagedscholarship.csuohio.edu'
    url = 'http://engagedscholarship.csuohio.edu/do/oai/'
    property_list = ['date', 'source', 'identifier', 'type', 'format', 'setSpec']
