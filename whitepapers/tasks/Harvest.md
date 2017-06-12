# Harvest Task

## Responsibilites
* Collect data from a remote source given a source config and date range
* Tease the collected data into individual blobs
* Extract SUIDs for each blob
* Store each (SUID, blob) pair as a RawDatum
* Spawn an IngestTask for each blob


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


## Steps

### Setup
* Load the source config and its required harvester
* NOT IMPLEMENTED: [Optimizations](#optimizations)
* Get or create `HarvestJob(start, end, source_config, harvester_version, source_config_version)`
  * If `HarvestJob` already exists, `HarvestJob.completions` is non-zero, and `superfluous` is not set, set `HarvestJob.status` to `skipped` and exit
* Obtain a Harvest lock on `source_config_id`
  * On failure:
    * if `force` is True, ignore and continue
    * if `force` is False, set `HarvestJob.status` to `rescheduled` and raise a `Retry`
* NOT IMPLEMENTED: [Check for consistent failures](#consistent-failures)
* Check `SourceConfig.disabled`
  * Unless `force` or `ignore_disabled` is `True`, crash
* Set `HarvestJob.status` to `started` and update `HarvestJob.date_started`.

### Actual work
* Harvest data between [`start`, `end`]
  * `RawDatum` should be populated regardless of exceptions
* For any data collected, link them to the `HarvestJob`
* If `ingest`, for any data collected, create an `IngestJob` and spawn an `IngestTask`
  * If `superfluous` is false, do not ingest any `RawDatum` that is an exact duplicate of previously harvested data.

### Clean up
* Set `HarvestJob.status` to `succeeded` and increment `HarvestJob.completions`

## Errors
If any errors arise while harvesting:
* Set `HarvestJob.status` to `failed` and `HarvestJob.context` to the traceback of the caught exception, or any other error information.
* Raise a `Retry`


## Future Improvements

### Consistent Failures
* Check the last `x` `HarvestJob`s of `SourceConfig`
  * If they are all `failed`, fail preemptively

### Optimizations
* Find `HarvestJob`s that cover the the span of `start` and `end`
  * Skip this task if they exist and are `succeeded`
* If the specified date range is >= [SOME LENGTH OF TIME] and `no_split` is False
  * Chunk the date range and spawn a harvest task for each chunk
  * Set status to `split` and exit
