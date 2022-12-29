import json

from share.exceptions import IngestError
from share.harvest.base import FetchResult
from share.tasks.jobs import IngestJobConsumer
from share.tasks.scheduler import IngestScheduler
from share import models as db


def chew(
    datum,
    datum_identifier,
    datum_contenttype,
    user,
    datestamp=None,
    transformer_key='v2_push',
) -> db.SourceUniqueIdentifier:
    """prepare a datum for ingestion
    """
    if isinstance(datum, (list, dict)):
        datum = json.dumps(datum, sort_keys=True)
    elif not isinstance(datum, str):
        raise IngestError('datum must be a string or a json-serializable dict or list')
    if not datum_identifier:
        raise IngestError('datum_identifier required (for suid\'s sake)')
    source_config = db.SourceConfig.objects.get_or_create_push_config(user, transformer_key)
    raw = db.RawDatum.objects.store_data(source_config, FetchResult(
        datum_identifier,
        datum,
        datestamp,
        datum_contenttype,
    ))
    return raw.suid


def swallow(suid, urgent=False) -> db.IngestJob:
    """set up the given suid to be digested soon
    """
    return IngestScheduler().schedule(suid, urgent=urgent)


def digest(suid):
    IngestJobConsumer().consume(suid.ingest_job.id)
