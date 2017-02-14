from stevedore import extension

from django.core.management.base import BaseCommand

from share.models import Harvester, Transformer


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.sync('share.harvesters', Harvester)
        self.sync('share.transformers', Transformer)

    def sync(self, namespace, model):
        names = extension.ExtensionManager(namespace).entry_points_names()
        for key in names:
            model.objects.update_or_create(key=key)
        missing = model.objects.exclude(key__in=names).values_list('key', flat=True)
        if missing:
            print('Missing {} subclasses: {}'.format(model._meta.model_name, missing))
