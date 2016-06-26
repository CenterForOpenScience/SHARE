from share.provider import OAIProviderAppConfig


class CogPrintsConfig(OAIProviderAppConfig):
    name = 'providers.be.ghent'
    title = 'ghent'
    long_title = 'Ghent University Academic Bibliography'
    home_page = 'https://biblio.ugent.be/'
    url = 'https://biblio.ugent.be/oai'
