import logging

from django.db import transaction


logger = logging.getLogger(__name__)


class Normalizer:

    def __init__(self, app_config):
        self.config = app_config

    def normalize(self, raw_data):
        # from share.models import Normalization
        from share.models import NormalizationQueue
        with transaction.atomic():
            try:
                models = self.do_normalize(raw_data)
                NormalizationQueue(data=raw_data).delete()
            except NormalizationQueue.DoesNotExist:
                pass

        print(raw_data)
        while models:
            x = models.pop(0)
            x.source = self.config.as_source()
            for field in x._meta.fields:
                if 'version' not in field.name:
                    setattr(x, field.name, getattr(x, field.name))
            try:
                x.save()
            except Exception as e:
                print(e)
                models.append(x)
            # Normalization(data=raw_data).save()

    def blocks(self, size=50):
        from share.models import NormalizationQueue
        ids = NormalizationQueue.objects.values_list('data_id', flat=True).filter(data__source=self.config.as_source(), )
        for i in range(0, len(ids), size):
            yield ids[i:i+50]
