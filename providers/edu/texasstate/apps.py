from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.texasstate'
    version = '0.0.1'
    title = 'texasstate'
    long_title = 'DSpace at Texas State University'
    home_page = 'https://digital.library.txstate.edu/'
    url = 'http://digital.library.txstate.edu/oai/request'
    approved_sets = [
        'com_10877_2',
        'com_10877_5',
        'com_10877_8',
        'com_10877_10',
        'com_10877_13',
        'com_10877_16',
        'com_10877_19',
        'com_10877_21',
        'com_10877_24',
        'com_10877_27',
        'com_10877_29',
        'com_10877_33',
        'com_10877_36',
        'com_10877_39',
        'com_10877_42',
        'com_10877_44',
        'com_10877_47',
        'com_10877_50',
        'com_10877_53',
        'com_10877_56',
        'com_10877_59',
        'com_10877_62',
        'com_10877_64',
        'com_10877_69',
        'com_10877_72',
        'com_10877_74',
        'com_10877_80',
        'com_10877_83',
        'com_10877_85',
        'com_10877_89',
        'com_10877_92',
        'com_10877_94',
        'com_10877_96',
        'com_10877_98',
        'com_10877_100',
        'com_10877_103',
        'com_10877_104',
        'com_10877_109',
        'com_10877_111',
        'com_10877_114',
        'com_10877_116',
        'com_10877_118',
        'com_10877_120',
        'com_10877_123',
        'com_10877_125',
        'com_10877_134',
        'com_10877_136',
        'com_10877_4332',
        'com_10877_4424',
        'com_10877_4425',
        'col_10877_78',
    ]
    property_list = [
        'type',
        'format',
        'date',
        'identifier',
        'setSpec',
        'source',
        'coverage',
        'relation',
        'rights',
    ]
