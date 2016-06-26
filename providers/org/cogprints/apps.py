from share.provider import OAIProviderAppConfig


class CogPrintsConfig(OAIProviderAppConfig):
    name = 'providers.org.cogprints'
    title = 'cogprints'
    long_title = 'Cognitive Sciences ePrint Archive'
    home_page = 'http://www.cogprints.org/'
    url = 'http://cogprints.org/cgi/oai2'
