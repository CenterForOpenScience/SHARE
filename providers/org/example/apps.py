from django.apps import AppConfig

from share.core import Harvester


class ExampleHarvester(Harvester):
    pass


class ExampleConfig(AppConfig):
    name = 'providers.org.example'
    HARVESTER = ExampleHarvester
    TITLE = 'Example Provider'
