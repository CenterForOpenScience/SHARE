from share.provider import ProviderAppConfig
from .harvester import ClinicalTrialsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.clinicaltrials'
    version = '0.0.1'
    title = 'clinicaltrials'
    long_title = 'ClinicalTrials.gov'
    home_page = 'https://clinicaltrials.gov/'
    harvester = ClinicalTrialsHarvester
