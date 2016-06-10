from django.apps import AppConfig

from share.core import Harvester


class ExampleHarvester(Harvester):
    pass


class ExampleConfig(AppConfig):
    name = 'harvesters.org.example'
    HARVESTER = ExampleHarvester
    TITLE = 'Example Harvester'
