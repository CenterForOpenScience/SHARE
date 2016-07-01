from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.utktrace'
    version = '0.0.1'
    title = 'utktrace'
    long_title = 'Trace: Tennessee Research and Creative Exchange'
    home_page = 'http://trace.tennessee.edu'
    url = 'http://trace.tennessee.edu/do/oai/'
