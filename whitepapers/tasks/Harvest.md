# Harvest Task

## Responsibilites
* Collecting data from a remote source given a source config and date range
* Teasing the collected data into individual blobs
* Extracting SUIDs for each blob
* Storing each (SUID, blob) pair as a RawDatum
* Spawning the transform task for each blob


## Considerations
* Harvesting MUST be able to respect rate limits
* Harvesting SHOULD be able to collect data from arbitrary date ranges
* Harvesting SHOULD NOT consume all available memory
* Harvesting SHOULD have a reasonable timeout


## Parameters
* `source_config_label` -- The label of the SourceConfig to use
* `start` -- The beginning of the date range to harvest
* `end` -- The end of the date range to harvest
* `limit` -- The maximum number of documents to collect. Defaults to `None` (Unlimited)
* `superfluous` -- Take certain actions that have previously suceeded. Defaults to `False`
* `ingest` -- Should collected data continue through the Ingest Pipeline? Defaults to `True`
* `no_split` -- Should run a single harvest job instead of splitting into many? Default to `False`
* `ignore_disabled` -- Run the task, even with disabled source configs
* `force` -- Force the task to run, against all odds


## Preface/Notes
* This tasks requires *2* connections to the same database
  * This allows the task to hold a lock while communicating progress to the outside world
* The second connection, `logging`, *should not* be in a transaction at any point in this task


## Steps

### Setup
* Load the source config and its required harvester
* Resolve `start` and `end` arguments to `date` objects
* NOT IMPLEMENTED: [Optimizations](#optimizations)
* Get or create `HarvestLog(start, end, source_config, harvester_version, source_config_version)`
  * If `HarvestLog` already exists, `HarvestLog.completions` is non-zero, and `superfluous` is not set, set `HarvestLog.status` to `skipped` and exit
* Begin a transaction in the `locking` connection
* Begin [catching exceptions](#catching-exceptions)
* Lock the `source_config` using the `locking` connection (NOWAIT)
  * On failure:
    * if `force` is True, ignore exception and continue
    * if `force` is False, set `HarvestLog.status` to `rescheduled` and raise a `Retry`
      * The total number of retries for this case should be high than other exceptions
* NOT IMPLEMENTED: [Check for consistent failures](#consistent-failures)
* Check `SourceConfig.disabled`
  * Unless `force` or `ignore_disabled` is `True`, crash
* Set `HarvestLog.status` to `started` and update `HarvestLog.date_started`.

### Actual work
* Begin a transaction in the `default` connection
* Harvest data between [`start`, `end`]
  * `RawDatum` should be populated regardless of exceptions
* For any data collected, link them to the `HarvestLog`
  * If linking fails, rollback the transaction using the `default` connection
    * If no exceptions where raised during harvesting, reraise this exception
* Commit the transaction using the `default` connection
* If any exceptions were raised during harvesting raise them now
* If `ingest`, for any data collected, spawn a `NormalizerTask` (NOT IMPLEMENTED: create an `IngestLog` and spawn an `IngestTask` instead)
  * If `superfluous` is false, do not start a `NormalizerTask` for any `RawDatum` that is an exact duplicate of previously harvested data.

### Clean up
* Set `HarvestLog.status` to `succeeded` and increment `HarvestLog.completions`

### Catching Exceptions
* Set `HarvestLog.status` to `failed` and `HarvestLog.context` to the traceback of the caught exception
* Rollback the transaction *only* on a DatabaseError or failing to link RawDatum to the `HarvestLog`
* Raise a `Retry`


## Future Improvements

### Consistent Failures
* Check the last `x` `HarvestLog`s of `SourceConfig`
  * If they are all `failed`, fail preemptively

### Optimizations
* Find `HarvestLog`s that cover the the span of `start` and `end`
  * Skip this task if they exist and are `succeeded`
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `split` and exit
