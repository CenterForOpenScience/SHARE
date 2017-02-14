# Transform Task


## Responsibilities
* Parsing data using source specific parsers
* Applying global cleaners to the data
* Catching any extranious exceptions and storing them in the ProcessLog and marking the ProcessLog as failed


## Parameters
* `raw_id` -- 
* `processor_version` --
* `cleaner_version` --
* `superfluous` --


## Steps

### Setup
* Load RawData by id.
  * Crash, if not found.
* If not defined set `processor_version` to the latest.
* If not defined set `cleaner_version` to the latest.
* Find and lock ProcessLog(`raw_id`, `processor_version`) (SELECT FOR UPDATE NOWAIT)
  * If not found, log an error. Create, Commit, Lock.
    * If the create fails, Log an error and exit.
  * If the lock times out/isn't granted. Log an error and exit.
* If the found ProcessLog's status is finished/done and `superfluous` is `False` exit.
* Set the status of the ProcessLog to in-progress

### Check for racing
* Search for any equivilent RawData (`document_id`, `source_id`) with an earlier timestamp that has not finished processing
  * If found set status to rescheduled and exit

### Actually process the data
* Start a transaction
* Load the processor
* Process data
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
* Set ProcessLog status to Done
