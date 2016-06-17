


class ClinicalTrialsConfig(ProviderAppConfig):
    name = 'providers.edu.asu'
    TITLE = 'asu'
    HARVESTER = FigshareHarvester

    SCHEDULE = crontab(minute=0, hour=0)
