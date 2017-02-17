# Harvest Task


## Responsibilites
* Collecting data from a remote source with a given date range
* Teasing the collected data into individual blobs
* Extracting source unique identifiers for each blob
* Storing each blob, identifier pair
* Spawning the transform task for each blob


## Considerations
* Ingestion MUST be able to respect rate limits
* Ingestion SHOULD be able to collect data from arbitrary date ranges
* Ingestion SHOULD NOT consume all available memory
* Ingestion SHOULD have a reasonable timeout


## Parameters
* `ingest_config_id` -- The PK of the IngestConfig to use
* `start_date` --
* `end_date` -- 
* `limit` -- The maximum number of documents to collect. Defaults to `None` (Unlimited)
* `superfluous` -- Take certain actions that have previously suceeded
* `transform` -- Should TransformJobs be launched for collected data. Defaults to `True`
* `ignore_disabled` -- Run the task, even with disabled ingest configs
* `force` -- Force the task to run, against all odds
* `no_split` -- `[*]` Should harvest jobs be split into multiple? Defaults to `False`
* `optimize` -- `[*]` Search for existing overlapping harvest logs. Defaults to `True`


## Steps

### Preventative measures
* If the specified `ingest_config` is disabled and `force` or `ignore_disabled` is not set, crash
* `[*]` For the given `ingest_config` find up to the last 5 harvest jobs with the same harvester versions
  * If they are all failed, throw an exception (Refuse to run)

### Setup
* Lock the `ingest_config` (NOWAIT)
  * On failure, set status to `RESCHEDULED` and throw a retry with a backoff. (This should be allowed to happen many times before finally failing)

### `[*]` Optimize (Not Implemented)
* Find other `HarvestLogs(ingest_config_id, harvester_version)` with in our `start_date`  and `end_date`
  * If found re-adjust our `start_date` and `end_date` and spawn other jobs as needed
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `SPLIT` and exit

### Setup (Cont)
* Get or create `HarvestLog(ingest_config_id, harvester_version, start_date, end_date)`
  * If found and status is:
    * `SUCCEEDED`, `SPLIT`, or `FAILED`: update timestamps and/or counts.
    * `STARTED`: Log a warning (Should not have been able to lock the `ingest_config`) and update timestamps and/or counts.
* Set `HarvestLog.status` to `STARTED` and `date_started` to now
* Load the harvester for the given `ingest_config`

### Actually Harvest
* Harvest data between the specified datetimes, respecting `limit` and `IngestConfig.rate_limit`

### Pass the data along
* Begin catching any exceptions
* For each piece of data recieved (Perferably in bulk/chunks)
  * Get or create `SourceUniqueIdentifier(identifier, ingest_config_id)`
  * Get or create `RawDatum(hash, suid)`
* For each piece of data (After saving to keep as transactional as possible)
  * Get or create `IngestLog(raw_id, ingest_config_id, transformer_version)`
    * If the log already exists and superfluous is not set, exit
  * Start the `IngestTask(raw_id, ingest_config_id)` unless `transform` is `False`

### Clean up
* If an exception was caught, set `HarvestLog.status` to `FAILED` and set `HarvestLog.error`
* Otherwise set status to `SUCCEEDED` and increment `HarvestLog.completions`
