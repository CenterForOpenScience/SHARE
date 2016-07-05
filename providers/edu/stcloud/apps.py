from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.stcloud'
    version = '0.0.1'
    title = 'stcloud'
    long_title = 'The repository at St Cloud State'
    home_page = 'http://stcloudstate.edu/'
    url = 'http://repository.stcloudstate.edu/do/oai/'
    approved_sets = [
        'ews_facpubs',
        'ews_wps',
        'hist_facwp',
        'comm_facpubs',
        'anth_facpubs',
        'soc_facpubs',
        'soc_ug_research',
        'chem_facpubs',
        'phys_present',
        'lrs_facpubs',
        'cfs_facpubs',
        'hurl_facpubs',
        'ed_facpubs',
        'cpcf_gradresearch',
        'econ_facpubs',
        'econ_wps',
        'econ_seminars',
        'stcloud_ling',
    ]
    property_list = ['type', 'source', 'format', 'setSpec', 'date']
