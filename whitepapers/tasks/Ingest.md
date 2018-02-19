# Ingest Task

## Responsibilities
* Load the most recent raw data for the given SUID.
* Transform the raw data into a MutableGraph.
* Apply source-specific and global regulations on the MutableGraph.
* Validate the regulated MutableGraph against a standard set of criteria and the SHARE data model.
* Update the SUID's existing set of States to match the validated MutableGraph.
* Keep the IngestJob for the given SUID accurate and up to date.
  * Catch any errors and add them to the IngestJob.
  * Store serialized snapshots of the MutableGraph after the Transform and Regulate steps in the IngestJob.


## Parameters
* `job_id` -- ID of the IngestJob for this task (optional)
* `superfluous` --


## Steps

### Setup
* If `job_id` is given, load the IngestJob
  * If not found, panic.
  * If `IngestJob.status` is `succeeded` and `superfluous` is `False`, exit.
* If `job_id` is not given, load any IngestJob that is in a ready state and unlocked
* Obtain an Ingest lock on the job's SUID
  * If the lock times out/isn't granted, set `IngestJob.status` to `rescheduled` and raise a `Retry`.
* Set `IngestJob.status` to `started` and update `IngestJob.date_started`


### Ingest
* [Transform](../ingest/Transformer.md)
  * Load the Transformer from the SUID's SourceConfig.
  * Update `IngestJob.transformer_version`.
  * Use the Transformer to transform the raw data into a [MutableGraph](../ingest/Graph.md).
  * Serialize the MutableGraph to `IngestJob.transformed_datum`.
* [Regulate](../ingest/Regulator.md)
  * Load the Regulator.
  * Update `IngestJob.regulator_version`.
  * Use the Regulator to clean the MutableGraph.
    * Save list of modifications with reasons to `IngestJob.regulator_logs`.
  * Serialize the cleaned MutableGraph to `IngestJob.regulated_datum`.
  * Use the Regulator to validate the cleaned MutableGraph.
* NOT IMPLEMENTED: [Consolidate](../ingest/Consolidator.md)
  * Load the Consolidator.
  * Update `IngestJob.consolidator_version`.
  * Use Consolidator to update the given SUID's States to match the validated MutableGraph.
* Legacy pipeline (Until Consolidator is implemented)
  * Serialize MutableGraph to JSON-LD and save as NormalizedData.
  * Spawn `disambiguate` task for the created NormalizedData.


### Cleanup
* Release all locks.
* Set `IngestJob.status` to `succeeded` and increment `IngestJob.completions`.


## Errors
If any errors arise while ingesting:
* Set `IngestJob.status` to `failed`.
* Set `IngestJob.context` to the traceback of the caught exception, or any other error information.
