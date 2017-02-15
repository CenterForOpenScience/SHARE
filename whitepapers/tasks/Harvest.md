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
* `source_config_id` -- The PK of the source to harvest from
* `start_date` --
* `end_date` -- 
* `limit` -- The maximum number of documents to collect. Defaults to `None` (Unlimitted)
* `rate_limit` -- Rate limit for network requests. Defaults to `None` (Unlimitted)
* `superfluous` -- Take certain actions that have previously suceeded
* `transform` -- Should TransformJobs be launched for collected data. Defaults to `True`
* `no_split` -- Should harvest jobs be split into multiple? Default to `False`
* `ignore_disabled` -- Run the task, even with disabled sources
* `force` -- Force the task to run, against all odds


## Steps

### Preventative measures
* If the specified `source_config` is disabled and `force` or `ignore_disabled` is not set, crash
* For the given `source_config` find up to the last 5 harvest jobs with the same versions
* If they are all failed, throw an exception (Refuse to run)

### Setup
* Lock the `source_config` (NOWAIT)
  * On failure, reschedule for a later run. (This should be allowed to happen many times before finally failing)
* Get or create `HarvestJob(source_config_id, version, harvester, date ranges...)`
  * if found and status is:
    * `SUCCEEDED`, `SPLIT`, or `FAILED`: update timestamps and/or counts.
    * STARTED: Log a warning (Should not have been able to lock the source) and update timestamps and/or counts.
* Set HarvestJob status to `STARTED`
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `SPLIT` and exit
* Load the harvester for the given `source_config`

### Actually Harvest
* Harvest data between the specified datetimes, respecting `limit` and `rate_limit`

### Pass the data along
* Begin catching any exceptions
* For each piece of data recieved (Perferably in bulk/chunks)
  * Get or create SourceUniqueIdentifier(suid, source_id)
  * Get or create RawData(hash, suid)
* For each piece of data (After saving to keep as transactional as possible)
  * Get or create TransformLogs(raw_id, version)
  * if the log already exists and superfluous is not set, exit
  * Start the transform task(raw_id, version) unless `transform` is `False`

### Clean up
* If an exception was caught, set status to `FAILED` and insert the exception/traceback
* Otherwise set status to `SUCCEEDED`
