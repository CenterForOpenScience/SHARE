from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.utaustin'
    version = '0.0.1'
    title = 'utaustin'
    long_title = 'University of Texas at Austin Digital Repository'
    home_page = 'https://repositories.lib.utexas.edu'
    url = 'https://repositories.lib.utexas.edu/utexas-oai/request'
    approved_sets = [
        'com_2152_1',
        'col_2152_13541',
        'col_2152_22957',
        'col_2152_13341',
        'col_2152_11183',
        'col_2152_15554',
        'col_2152_21116',
        'col_2152_11227',
        'col_2152_26',
        'col_2152_25673',
        'col_2152_21442',
        'col_2152_11019',
        'col_2152_10079',
        'col_2152_23952',
        'com_2152_19781',
        'com_2152_4',
        'com_2152_5',
        'com_2152_15265',
        'com_2152_20099',
        'com_2152_4027',
        'col_2152_22392',
        'com_2152_24880',
        'com_2152_24538',
        'col_2152_20329',
        'com_2152_14283',
        'col_2152_14697',
        'col_2152_16482',
        'com_2152_24831',
        'com_2152_11681',
        'com_2152_15722',
        'col_2152_7103',
        'col_2152_20398',
        'col_2152_7100',
        'col_2152_7105',
        'col_2152_7102',
        'col_2152_7101',
        'col_2152_17706',
        'col_2152_15040',
        'col_2152_14309',
        'col_2152_18015',
        'com_2152_6854',
        'com_2152_6851',
        'col_2152_1508',
    ]
    property_list = ['type', 'source', 'format', 'date', 'identifier', 'setSpec', 'rights']
