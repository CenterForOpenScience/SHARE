# Ingest Task


## Responsibilities
* Parsing data using source-specific parsers
* Applying global cleaners to the data
* Catching any extraneous exceptions, storing them in the TransformLog, and marking the TransformLog `FAILED`


## Parameters
* `raw_id` -- 
* `transformer_version` --
* `regulator_version` --
* `superfluous` --


## Steps

### Setup
* Load RawData by id.
  * Crash, if not found.
* If not defined set `transformer_version` to the latest.
* If not defined set `regulator_version` to the latest.
* Find and lock TransformLog(`raw_id`, `transformer_version`) (SELECT FOR UPDATE NOWAIT)
  * If not found, log an error. Create, Commit, Lock.
    * If the create fails, log an error and exit.
  * If the lock times out/isn't granted. Log an error and exit.
* If the found TransformLog's status is `SUCCEEDED` and `superfluous` is `False` exit.
* Set the status of the TransformLog to `STARTED`

### Check for racing
* Search for any equivalent RawData (`document_id`, `source_id`) with an earlier timestamp that has not finished transfoming
  * If found set status to `RESCHEDULED` and exit

### Actually transform the data
* Start a transaction
* Load the transformer
* Transform data
* Load the cleaning suite
* Clean data

### Diffing
* Load and lock all the states, if any, for this RawData
* Diff the states
  * A more presumptuous form of disambiguation should be used here to match as many nodes as possible
  * Double check that dates are not going back in time (May be indicitive of a race)
* Create/update the states as necessary
  * Any existing nodes that have had nothing disambiguated to them may be considered removed/deleted
  * Ensure that internal modification dates are not bumped if no changes have been made

### Cleanup
* Commit transaction
* Release all locks
* Start disambiguation tasks for updated states
* Set TransformLog status to `SUCCEEDED`
