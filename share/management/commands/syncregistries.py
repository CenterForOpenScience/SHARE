from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.harvest import BaseHarvester
from share.models import Harvester, Transformer
from share.transform import BaseTransformer


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.sync(BaseHarvester.registry, Harvester)
        self.sync(BaseTransformer.registry, Transformer)
        
    def sync(self, registry, model):
        for key, obj in registry.items():
            model.objects.update_or_create(key=key)
        model.objects.exclude(key__in=registry.keys()).delete()
