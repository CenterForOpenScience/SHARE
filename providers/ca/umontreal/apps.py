from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ca.umontreal'
    version = '0.0.1'
    title = 'umontreal'
    long_title = "PAPYRUS - Dépôt institutionnel de l'Université de Montréal"
    home_page = 'http://papyrus.bib.umontreal.ca'
    url = 'http://papyrus.bib.umontreal.ca/oai/request'
