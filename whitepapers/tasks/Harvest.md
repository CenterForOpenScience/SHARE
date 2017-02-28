# Harvest Task


## Responsibilites
* Collecting data from a remote source with a given date range
* Teasing the collected data into individual blobs
* Extracting source unique identifiers for each blob
* Storing each blob, identifier pair
* Spawning the transform task for each blob


## Considerations
* Harvesting MUST be able to respect rate limits
* Harvesting SHOULD be able to collect data from arbitrary date ranges
* Harvesting SHOULD NOT consume all available memory
* Harvesting SHOULD have a reasonable timeout


## Parameters
* `source_config_id` -- The PK of the SourceConfig to use
* `start_date` --
* `end_date` -- 
* `limit` -- The maximum number of documents to collect. Defaults to `None` (Unlimited)
* `superfluous` -- Take certain actions that have previously suceeded
* `transform` -- Should TransformJobs be launched for collected data. Defaults to `True`
* `no_split` -- Should harvest jobs be split into multiple? Default to `False`
* `ignore_disabled` -- Run the task, even with disabled source configs
* `force` -- Force the task to run, against all odds


## Steps

### Preventative measures
* If the specified `source_config` is disabled and `force` or `ignore_disabled` is not set, crash
* For the given `source_config` find up to the last 5 harvest jobs with the same harvester versions
* If they are all failed, throw an exception (Refuse to run)

### Setup
* Lock the `source_config` (NOWAIT)
  * On failure, reschedule for a later run. (This should be allowed to happen many times before finally failing)
* Get or create HarvestLog(`source_config_id`, `harvester_version`, `start_date`, `end_date`)
  * if found and status is:
    * `SUCCEEDED`, `SPLIT`, or `FAILED`: update timestamps and/or counts.
    * `STARTED`: Log a warning (Should not have been able to lock the `source_config`) and update timestamps and/or counts.
* Set HarvestLog status to `STARTED`
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `SPLIT` and exit
* Load the harvester for the given `source_config`

### Actually Harvest
* Harvest data between the specified datetimes, respecting `limit` and `source_config.rate_limit`

### Pass the data along
* Begin catching any exceptions
* For each piece of data recieved (Perferably in bulk/chunks)
  * Get or create `SourceUniqueIdentifier(suid, source_id)`
    * Question: Should SUIDs depend on `source_config_id` instead of `source_id`? If we're harvesting data in multiple formats from the same source, we probably want to keep the respective states separate.
  * Get or create RawData(hash, suid)
* For each piece of data (After saving to keep as transactional as possible)
  * Get or create `TransformLog(raw_id, source_config_id, transformer_version)`
  * if the log already exists and superfluous is not set, exit
  * Start the `TransformTask(raw_id, source_config_id)` unless `transform` is `False`

### Clean up
* If an exception was caught, set status to `FAILED` and insert the exception/traceback
* Otherwise set status to `SUCCEEDED`
