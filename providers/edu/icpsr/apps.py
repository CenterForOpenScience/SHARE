from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.icpsr'
    title = 'icpsr'
    long_title = 'Inter-University Consortium for Political and Social Research'
    home_page = 'http://www.icpsr.umich.edu/'
    url = 'http://www.icpsr.umich.edu/icpsrweb/ICPSR/oai/studies'
    timezone_granularity = False
