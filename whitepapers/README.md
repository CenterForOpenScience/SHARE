# The SHARE Pipeline

## Vocabulary

* SHARE Object -- Generic term for any data type from the SHARE data set. eg CreativeWork, WorkIdentifier, etc.
* SUID -- Source unique identifier.
* State -- Source specific version of a given SHARE Object.
* Final -- The representation of an object in the publicly accessibly SHARE dataset.
* Harvest -- Collecting data from 
* Transform --
* [Data] Cleaning --
* TCT -- Transform Clean Task.
* Normalize -- Defunct; see Transform.

## Overview

### Main pipeline:

* Data Ingest Task -- Collect and store data
* Data Process Task -- Parse and clean data

### Auxillary Tasks

* Data Disambiguate Task -- Link together individual records
* Data Build Task -- Intellgently aggregate records describing the same object

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
