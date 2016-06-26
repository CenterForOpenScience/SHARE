from share.provider import ProviderAppConfig
from .harvester import ClinicalTrialsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.clinicaltrials'
    title = 'clinicaltrials'
    long_title = 'ClinicalTrials.gov'
    home_page = 'https://clinicaltrials.gov/'
    harvester = ClinicalTrialsHarvester
