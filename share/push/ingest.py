"""ingest: chew, swallow, digest

chew: store by checksum
swallow: queue for digestion
digest:
    extract metadata as rdfgraph
    reformat metadata as desired
    index as is helpful to query
"""


import json

from share.exceptions import IngestError
from share.extract import get_rdf_extractor_class
from share.harvest.base import FetchResult
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

    create (or update) one of each of:
        Source (from whom/where is it?)
        SourceConfig (how did/do we get it?)
        SourceUniqueIdentifier (by what name do/would they know it?)
        RawDatum ("it", a metadata record)
    """
    if not datum_identifier:
        raise IngestError('datum_identifier required (for suid\'s sake)')

    if isinstance(datum, (list, dict)):
        datum = json.dumps(datum, sort_keys=True)
    elif isinstance(datum, bytes):
        datum = datum.decode()

    if not isinstance(datum, str):
        raise IngestError('datum must be a string or a json-serializable dict or list')
    source_config = db.SourceConfig.objects.get_or_create_push_config(user, transformer_key)
    raw = db.RawDatum.objects.store_data(source_config, FetchResult(
        datum_identifier,
        datum,
        datestamp,
        datum_contenttype,
    ))
    return raw.suid


def swallow(suid) -> db.IngestJob:
    """set up the given suid to be digested soon

    create (or update) an IngestJob and enqueue a task
    """
    return IngestScheduler().schedule(suid)


def digest(suid):
    """extract, format, index

    """
    ingest_job = IngestScheduler().schedule(suid, claim=True)
    IngestJobConsumer().consume(job_id=ingest_job.id, exhaust=False)


def extract(raw):
    extracted_normalized_datum = None
    extractor = get_rdf_extractor_class(raw.contenttype)(raw.suid.source_config)
    rdfgraph = extractor.extract_resource_description(raw.datum, raw.suid.described_resource_pid)
    if rdfgraph:
        extracted_normalized_datum = db.NormalizedData(
            source=raw.suid.source_config.source.user,
            raw=raw,
            rdfgraph=rdfgraph,
        )
        extracted_normalized_datum.save()
    raw.no_output = bool(rdfgraph)
    raw.save(update_fields=['no_output'])
    return extracted_normalized_datum


def reformat(normalized_datum):
    db.FormattedMetadataRecord.objects.save_formatted_records(
        normalized_datum.raw.suid,
        normalized_datum=normalized_datum,
    )


def index(suid, urgent):
    indexer = SearchIndexer()
    indexer.send_messages(MessageType.INDEX_SUID, [suid.id], urgent=urgent)
