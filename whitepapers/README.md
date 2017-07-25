# The SHARE System Spec

This set of documents exist to both formalize and restructure how information is processed by SHARE.
Over time the "pipline" has changed significantly from its original inception. The vocabulary to describe the process has not, leading to a decent amount of confusion.

## Vocabulary

* SHARE Object -- Generic term for any data type from the SHARE data set. eg CreativeWork, WorkIdentifier, etc.
* SUID -- Source unique identifier.
* State -- Source specific version of a given SHARE Object.
* Final -- The representation of an object in the publicly accessibly SHARE dataset.
* Harvest -- Collecting data from 
* Normalize -- Defunct; see Transform.
* Harvester -- Code responsible for aquiring data to be processed by SHARE
* Transformer -- Code responsible for reformatting harvested data into a SHARE compliant format
* Regulators -- Code responsible for cleaning and validating values expelled by a transformer
* Deduplicator -- The job/code responsible for matching states together to be assembled into the final data set
* Assembler -- The code responsible for selecting the best attributes from individual states

### Why did you pick X word?
* Harvest -- The meaning of this word never actually changed. Used for historic reasons.
* [Transform](http://www.dictionary.com/browse/transform) -- To change in form, appearance, or structure; metamorphose.
* [Regulate](http://www.dictionary.com/browse/regulate) -- To control or direct by a rule, principle, method, etc.
* [Deduplicate]() --
* [Assemble](http://www.dictionary.com/browse/assemble) -- To put or fit together; put together the parts of.

## Overview

### There is no pipeline

```
                 +--------------------------------------------+
+---------+      |                  Ingest                    |
| Harvest | ---> | Transform  --->  Regulate ---> Consolidate |
+---------+      +--------------------------------------------+

+---------------+
| Deduplication |
+---------------+

+----------+
| Assemble |
+----------+
```

At first glance, the SHARE workflow may appear to be a pipeline. It is not. Data only addressed a single enity, briefly, in the begining of the workflow.
Once data is full processed, it is treated as part of a whole. All jobs, aside from the first two boxes, operate on the dataset as a whole.

### Janitor

There will be a set of "Janitor" tasks that will:
* Process un processed data
* Re-process data if a new processor has been added
* Healing broken data
* Clean up deleted records or records that no longer exist

## FAQ

### Will I be able to see what data sources an object came from?
Yes, `SELECT source_id FROM SHAREObject_state WHERE final_id = x`

### Help! Objects have been incorrectly merged together or the data is wrong!
This falls into 1 of 3 scenarios.

#### Scenario 1: Our data processor has a bug
The processor bug gets fixed and its version is bumped.

#### Scenario 2: Our disambiguation has a bug
The disambiguator bug gets fixed and its version is bumped.

#### Scenario 3: We have recieved incorrect data
The incorrect data must be corrected by someone or removed from the dataset.

#### Finally
When The Janitor comes along, it will detect and out of date data and trigger rebuilds for it.
The rebuilds will heal any issues in the final dataset



Single global diambigation task
Store tags and subjects as arrays
SUIDS as another table. Lock to prevent racing on rawdata updating

# Ideas
Counters for started, finished, etc on log jobs
Janitor actually deletes states marked as `is_deleted`

Move sources to their own table


Harvesters
Transformers
Regulators


Deduplicator
Assembler
