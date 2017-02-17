# Harvesting

## Changes
* Renamed `RawData` -> `RawDatum`
* Added a new layer of task tracking `HarvestLog`
* Stripped date fields off of `RawData`
* `provider_doc_id` moved into its own model
* `RawDatum` will no longer be connected to `CeleryTask`

## Migrating
### Prerequisites
The `Source`, `SourceConfig`, `Harvester`, and `Transformer` models.

1. Rename `RawData` -> `RawDatum` (Done first for clarity)
2. Create the `SourceUniqueIdentifier` table
3. Populate `SourceUniqueIdentifier` with existing `RawDatum`.
  * `provider_doc_id` -> `SourceUniqueIdentifier.identifier`
  * `app_label` -> `SourceUniqueIdentifier.source_config_id`
4. Drop `provider_doc_id`, `source_id`, and `app_label`
5. The though-table connecting `RawDatum` to `CeleryTask` may be removed at this point.
6. Using `date_seen` and `date_created` begin to slowly re-harvest providers attempting to find these data again
7. Once all, or a sufficient amount, of data are linked to a `HarvestLog`, the date fields can be dropped.


## User Stories



## Tables
### RawDatum
Raw datum, exactly as it was given to SHARE.

| Column         | Type | Indexed | Nullable | FK  | Default | Description                                                        |
| :------------- | :--: | :-----: | :------: | :-: | :-----: | :----------------------------------------------------------------- |
| `suid_id`      | int  |    ✓    |          |  ✓  |         | SUID for this datum                                                |
| `datum`        | text |         |          |     |         | The raw datum itself (typically JSON or XML string)                |
| `sha256`       | text | unique  |          |     |         | SHA-256 hash of `data`                                             |
| `harvest_logs` | m2m  |         |          |     |         | List of HarvestLogs for harvester runs that found this exact datum |

### HarvestLog
Log entries to track the status of a specific harvester run.

| Column                  |   Type    | Indexed | Nullable | FK  |     Default     | Description                                                                                                   |
| :---------------------- | :-------: | :-----: | :------: | :-: | :-------------: | :------------------------------------------------------------------------------------------------------------ |
| `source_config_id`      |    int    |    ✓    |          |  ✓  |                 | IngestConfig for this harvester run                                                                           |
| `start_date`            | datetime  |    ✓    |          |     |                 | Beginning of the date range to harvest                                                                        |
| `end_date`              | datetime  |    ✓    |          |     |                 | End of the date range to harvest                                                                              |
| `status`                | enum(int) |    ✓    |          |     |     CREATED     | Status of the harvester run, one of {CREATED, STARTED, SPLIT, SUCCEEDED, FAILED, RESCHEDULED, SKIPPED}        |
| `error`                 |   text    |         |          |     |       ""        | A custom error message or traceback describing why this job failed                                            |
| `completions`           |    int    |         |          |     |        0        | The number of times `status` has been set to SUCCEEDED                                                        |
| `date_started`          | datetime  |         |          |     |                 | Datetime `status` was last set to STARTED                                                                     |
| `date_created`          | datetime  |         |          |     |       now       | Datetime this row was created                                                                                 |
| `date_modified`         | datetime  |         |          |     | now (on update) | Datetime this row was last modified                                                                           |
| `share_version`         |   text    |         |          |     |     UNKNOWN     | The commitish at the time this job was last run                                                               |
| `harvester_version`     |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the harvester, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010')      |
| `source_config_version` |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the `SourceConfig`, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010') |

#### Other indices
* `source_config_id`, `harvester_version`, `start_date`, `end_date` (unique)

### HarvestLogRawDatum
Through-table that links a `RawDatum` to a `HarvestLog`. (Let Django generate this)

| Column           | Type | Indexed | Nullable | FK  | Default | Description |
| :--------------- | :--: | :-----: | :------: | :-: | :-----: | :---------- |
| `harvest_log_id` | int  |    ✓    |          |  ✓  |         |             |
| `rawdatum_id`    | int  |    ✓    |          |  ✓  |         |             |


#### Notes
* In the future, jobs may attempt to optimize themselves by searching for jobs that have already harvested a section of it required date range
* In the future, jobs may be merged together if they have overlapping date ranges to save on table space


## FAQ
