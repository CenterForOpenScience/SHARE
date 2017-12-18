import json
import uuid

from share.models import IngestJob
from share.models import RawDatum
from share.models import SourceConfig
from share.tasks import ingest


class Ingester:
    """Helper class that takes a datum and feeds it to SHARE

    Usage given a source config:
        Ingester(datum, datum_id).with_config(source_config).ingest()

    Usage given a user and transformer:
        Ingester(datum, datum_id).as_user(user, 'transformer_key').ingest()
    """

    raw = None
    job = None
    async_task = None

    _config = None

    def __init__(self, datum, datum_id=None, datestamp=None):
        if isinstance(datum, str):
            self.datum = datum
        elif isinstance(datum, (list, dict)):
            self.datum = json.dumps(datum, sort_keys=True)
        else:
            raise TypeError('datum must be a string or a json-serializable dict or list')

        self.datum_id = datum_id if datum_id else str(uuid.uuid4())
        self.datestamp = datestamp

    def with_config(self, config):
        assert not self._config
        self._config = config
        return self

    def as_user(self, user, transformer_key='v2_push'):
        """Ingest as the given user, with the given transformer

        Create a source config for the given user/transformer, or get a previously created one.
        """
        assert not self._config
        self._config = SourceConfig.objects.get_or_create_push_config(user, transformer_key)
        return self

    def ingest(self, **kwargs):
        assert 'job_id' not in kwargs
        self._setup_ingest()
        # Here comes the airplane!
        ingest(job_id=self.job.id, exhaust=False, **kwargs)
        return self

    def ingest_async(self, **kwargs):
        assert 'job_id' not in kwargs
        self._setup_ingest()
        # There's pizza in the fridge.
        self.async_task = ingest.delay(job_id=self.job.id, exhaust=False, **kwargs)
        return self

    def _setup_ingest(self):
        assert self.datum and self._config and not (self.raw or self.job or self.async_task)

        # TODO get rid of FetchResult, or make it more sensical
        from share.harvest.base import FetchResult
        fetch_result = FetchResult(self.datum_id, self.datum, self.datestamp)
        self.raw = RawDatum.objects.store_data(self._config, fetch_result)
        self.job = IngestJob.schedule(self.raw)
