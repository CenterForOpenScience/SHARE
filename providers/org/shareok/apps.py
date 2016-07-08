from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.shareok'
    version = '0.0.1'
    title = 'shareok'
    long_title = 'SHAREOK Repository'
    home_page = 'https://shareok.org'
    url = 'https://shareok.org/oai/request'
    approved_sets = [
        'com_11244_14447',
        'com_11244_1',
        'col_11244_14248',
        'com_11244_6231',
        'col_11244_7929',
        'col_11244_7920',
        'col_11244_10476',
        'com_11244_10465',
        'com_11244_10460',
        'col_11244_10466',
        'col_11244_10464',
        'col_11244_10462',
        'com_11244_15231',
        'col_11244_15285',
        'col_11244_15479',
        'col_11244_20910',
        'col_11244_20927',
        'col_11244_21724',
        'col_11244_22702',
        'col_11244_23528',
    ]
