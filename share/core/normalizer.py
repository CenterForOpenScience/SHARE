import logging

from django.db import transaction


logger = logging.getLogger(__name__)


class Normalizer:

    def __init__(self, app_config):
        self.config = app_config

    def normalize(self, raw_data):
        from share.models import Normalization
        from share.models import NormalizationQueue
        with transaction.atomic():
            try:
                NormalizationQueue(data=raw_data).delete()
            except NormalizationQueue.NotFound:
                pass
            Normalization(data=raw_data).save()

    def blocks(self, size=50):
        from share.models import NormalizationQueue
        ids = NormalizationQueue.objects.values_list('data.id', flat=True).filter(data__source=self.config.as_source(), )
        for i in range(0, len(ids), size):
            yield ids[i:i+50]
