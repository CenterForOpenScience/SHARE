from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.scholarsarchiveosu'
    version = '0.0.1'
    title = 'scholarsarchiveosu'
    long_title = 'ScholarsArchive@OSU'
    home_page = 'http://ir.library.oregonstate.edu/'
    url = 'http://ir.library.oregonstate.edu/oai/request'
