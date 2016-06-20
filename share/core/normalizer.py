import abc


class Normalizer(metaclass=abc.ABCMeta):

    def __init__(self, app_config):
        self.config = app_config

    @abc.abstractmethod
    def do_normalize(self, raw_data):
        raise NotImplementedError

    def normalize(self, raw_data):
        from share.parsers import ctx  # TODO Fix circular import

        # Parsed data will be loaded into ctx
        self.do_normalize(raw_data)
        jsonld = ctx.jsonld
        ctx.clear()

        return jsonld

    def blocks(self, size=50):
        from share.models import NormalizationQueue
        ids = NormalizationQueue.objects.values_list('data_id', flat=True).filter(data__source=self.config.as_source(), )
        for i in range(0, len(ids), size):
            yield ids[i:i+50]
