from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.{{cookiecutter.domain}}.{{cookiecutter.title}}'
    version = '0.0.1'
    title = '{{cookiecutter.title}}'
    long_title = '{{cookiecutter.long_title}}'
    home_page = '{{cookiecutter.home_page}}'
    url = '{{cookiecutter.url}}'
    # approved_sets = TODO if necessary
    # time_granularity = TODO if necessary
