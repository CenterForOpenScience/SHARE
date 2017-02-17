

## Responsibilites
* Collecting data from a remote source with a given date range
* Teasing the collected data into individual blobs
* Extracting source unique identifiers for each blob
* Storing each blob, identifier pair
* Spawning the transform task for each blob


## Considerations
* Harvesters MUST be able to respect rate limits
* Harvesters SHOULD be able to collect data from arbitrary date ranges
* Harvesters SHOULD NOT consume all available memory
* Harvesters SHOULD have a reasonable timeout


## Parameters
* `source_config_id` -- The PK of the IngestConfig to use
* `start_date` --
* `end_date` -- 
* `limit` -- The maximum number of documents to collect. Defaults to `None` (Unlimited)
* `superfluous` -- Take certain actions that have previously suceeded
* `transform` -- Should TransformJobs be launched for collected data. Defaults to `True`
* `no_split` -- Should harvest jobs be split into multiple? Default to `False`
* `ignore_disabled` -- Run the task, even with disabled ingest configs
* `force` -- Force the task to run, against all odds


## Preface/Notes
* This tasks requires *2* connections to the same database
  * This allows the task to hold a lock while communicating progress to the outside world
* The second connection, `logging`, *should not* be in a transaction at any point in this task


## Steps

### Setup
* Resolve `start` and `end` arguments to `datetime` objects
* Load the required harvester
* NOT IMPLEMENTED [Optimizations](#optimizations)
* Get or create `HarvestLog(start, end, source_config, harvester_version, source_config_version)`
  * If created, `HarvestLog.status` is SUCCEEDED or SKIPPED, and `superfluous` is not set, set `HarvestLog.status` to SKIPPED and exit
* Begin [catching exceptions](#catching-exceptions)
* Begin a transaction in the `locking` connection
* Lock the `source_config` using the `locking` connection (NOWAIT)
  * On failure:
    * Force = True, Ignore exception and continue
    * Force = False, Set `HarvestLog.status` to RESCHEDULED and raise a `Retry`
      * The total number of retries for this case should be high than other exceptions
* NOT IMPLEMENTED [Check for consistent failures](#consistent-failures)
* Check `SourceConfig.disabled`
  * Unless `force` or `ignore_disabled` is `True`, crash
* Set `HarvestLog.status` to STARTED and update `HarvestLog.date_started`.

### Actual work
* Begin a transaction in the `default` connection
* Harvest data between [`start`, `end`]
  * `RawData` should be populated regardless of exceptions
* For any data collected, link them to `log`
  * If linking fails, rollback the transaction using the `default` connection
    * If no exceptions where raised during harvesting, reraise this exception
* Commit the transaction using the `default` connection
* If any exceptions were raised during harvesting raise them now
* If `transform`, for any data collected, create an `IngestLog` and spawn an `IngestTask`

### Clean up
* Set `HarvestLog.status` to SUCCEEDED and increment `HarvestLog.completions`

### Catching Exceptions
* Set `HarvestLog.status` to FAILED and `HarvestLog.error` to the traceback of the caught exception
* Rollback the transaction *only* if creating
* Raise a `Retry`


## Future Improvements

### Consitent Failures
* Check the last `x` `HarvestLog`s of `SourceConfig`
  * If they are all FAILED, fail preemptively

### Optimizations
* Find `HarvestLog`s that cover the the span of `start` and `end`
  * Skip this task if they exist and are SUCCEEDED
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `SPLIT` and exit
