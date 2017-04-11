# Ingest Task

## Responsibilities
* Load the most recent raw data for the given SUID.
* Transform the raw data into a StateGraph.
* Apply source-specific and global regulations on the StateGraph.
* Validate the regulated StateGraph against a standard set of criteria and the SHARE data model.
* Update the SUID's existing set of States to match the validated StateGraph.
* Keep the IngestLog for the given SUID accurate and up to date.
  * Catch any errors and add them to the IngestLog.
  * Store serialized snapshots of the StateGraph after the Transform and Regulate steps in the IngestLog.


## Parameters
* `ingest_log_id` -- ID of the IngestLog for this task
* `superfluous` --


## Steps

### Setup
* Load the IngestLog
  * If not found, panic.
  * If `IngestLog.status` is `succeeded` and `superfluous` is `False`, exit.
* Obtain an Ingest lock on `suid_id`
  * If the lock times out/isn't granted, set `IngestLog.status` to `rescheduled` and raise a retry.
* Load the most recent RawDatum for the given SUID.
  * If not found, log an error and exit.
  * TODO: Once `RawDatum.partial` is implemented, load all raw data from the most recent back to the last with `partial=False`.
  * If the SUID's latest RawDatum is more recent than `IngestLog.latest_raw_id`, update `IngestLog.latest_raw_id`
    * If update violates unique constraint, exit. Another task has already ingested the latest data.
* Set `IngestLog.status` to `started` and update `IngestLog.date_started`


### Ingest
* Transform
  * Load the Transformer from the SUID's SourceConfig.
  * Update `IngestLog.transformer_version`.
  * Use the Transformer to transform the raw data into a StateGraph.
  * Serialize the StateGraph to `IngestLog.transformed_data`.
* Regulate
  * Load the Regulator.
  * Update `IngestLog.regulator_version`.
  * Use the Regulator to clean the StateGraph.
    * Save list of modifications with reasons to `IngestLog.regulator_log`.
  * Serialize the cleaned StateGraph to `IngestLog.regulated_data`.
  * Use the Regulator to validate the cleaned StateGraph.
* NOT IMPLEMENTED: Consolidate
  * Load the Consolidator.
  * Update `IngestLog.consolidator_version`.
  * Use Consolidator to update the given SUID's States to match the validated StateGraph.
* Until Consolidator is implemented:
  * Serialize StateGraph to JSON-LD and save as NormalizedData.
  * Spawn DisambiguatorTask for the created NormalizedData.


### Cleanup
* Release all locks.
* Set `IngestLog.status` to `succeeded` and increment `IngestLog.completions`.


## Errors
If any errors arise during ingestion:
* Set `IngestLog.status` to `failed`.
* Set `IngestLog.context` to the exception or any error information.
* Exit.
