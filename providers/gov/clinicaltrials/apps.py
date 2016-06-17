



class ClinicalTrialsConfig(ProviderAppConfig):
    name = 'providers.edu.asu'
    TITLE = 'asu'
    HARVESTER = ClinicalTrialsHarvester

    SCHEDULE = crontab(minute=0, hour=0)
