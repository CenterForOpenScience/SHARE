# SQL Tables

## Template

### {ModelName}
{Description}

| Column | Type | Indexed | Nullable | FK  | Default | Description |
| :----- | :--: | :-----: | :------: | :-: | :-----: | :---------- |
|        |      |    ✓    |    ✓     |  ✓  |         |             |

#### Other indices
* `{column_name}`, `{column_name}`, ... [(unique)]
* ...

#### Notes
* ...

## Data

### SourceUniqueIdentifier (SUID)
Identifier for a specific document from a specific source.

| Column             | Type | Indexed | Nullable | FK  | Default | Description                                    |
| :----------------- | :--: | :-----: | :------: | :-: | :-----: | :--------------------------------------------- |
| `identifier`       | text |         |          |     |         | Identifier given to the document by the source |
| `ingest_config_id` | int  |    ✓    |          |  ✓  |         | IngestConfig used to ingest the document       |

#### Other indices
* `source_doc_id`, `ingest_config_id` (unique)

### RawDatum
Raw datum, exactly as it was given to SHARE.

| Column         | Type | Indexed | Nullable | FK  | Default | Description                                                        |
| :------------- | :--: | :-----: | :------: | :-: | :-----: | :----------------------------------------------------------------- |
| `suid_id`      | int  |    ✓    |          |  ✓  |         | SUID for this datum                                                |
| `datum`        | text |         |          |     |         | The raw datum itself (typically JSON or XML string)                |
| `sha256`       | text | unique  |          |     |         | SHA-256 hash of `data`                                             |
| `harvest_logs` | m2m  |         |          |     |         | List of HarvestLogs for harvester runs that found this exact datum |

## Ingest Configuration

### IngestConfig
Describes one way to harvest metadata from a Source, and how to transform the result.

| Column                 | Type  | Indexed | Nullable | FK  |   Default   | Description                                                                                         |
| :--------------------- | :---: | :-----: | :------: | :-: | :---------: | :-------------------------------------------------------------------------------------------------- |
| `source_id`            |  int  |    ✓    |          |  ✓  |             | Source to harvest from                                                                              |
| `base_url`             | text  |         |          |     |             | URL of the API or endpoint where the metadata is available                                          |
| `earliest_date`        | date  |         |    ✓     |     |             | Earliest date with available data                                                                   |
| `rate_limit_allowance` |  int  |         |          |     |      5      | Number of requests allowed every `rate_limit_period` seconds                                        |
| `rate_limit_period`    |  int  |         |          |     |      1      | Number of seconds for every `rate_limit_allowance` requests                                         |
| `harvester_id`         |  int  |    ✓    |          |  ✓  |             | Harvester to use                                                                                    |
| `harvester_kwargs`     | jsonb |         |    ✓     |     |             | JSON object passed to the harvester as kwargs                                                       |
| `transformer_id`       |  int  |    ✓    |          |  ✓  |             | Transformer to use                                                                                  |
| `transformer_kwargs`   | jsonb |         |    ✓     |     |             | JSON object passed to the transformer as kwargs, along with the harvested raw datum                 |
| `disabled`             | bool  |         |          |     |    False    | True if this ingest config should not be run automatically                                          |
| `version`              | text  |    ✓    |          |     | 000.000.000 | Semantic version of this row, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010') |

### Source
A Source is a place metadata comes from.

| Column       | Type  | Indexed | Nullable | FK  | Default | Description                                                                                      |
| :----------- | :---: | :-----: | :------: | :-: | :-----: | :----------------------------------------------------------------------------------------------- |
| `name`       | text  | unique  |          |     |         | Short name                                                                                       |
| `long_title` | text  | unique  |          |     |         | Full, human-friendly name                                                                        |
| `home_page`  | text  |         |    ✓     |     |         | URL                                                                                              |
| `icon`       | image |         |    ✓     |     |         | Recognizable icon for the source                                                                 |
| `user_id`    |  int  |         |          |  ✓  |         | User with permission to submit data as this source (TODO: replace with django permissions stuff) |

### Harvester
Each row corresponds to a Harvester implementation in python. (TODO: describe those somewhere)

| Column          |   Type   | Indexed | Nullable | FK  |     Default     | Description                                                      |
| :-------------- | :------: | :-----: | :------: | :-: | :-------------: | :--------------------------------------------------------------- |
| `key`           |   text   | unique  |          |     |                 | Key that can be used to get the corresponding Harvester subclass |
| `date_created`  | datetime |         |          |     |       now       |                                                                  |
| `date_modified` | datetime |         |          |     | now (on update) |                                                                  |

### Transformer
Each row corresponds to a Transformer implementation in python. (TODO: describe those somewhere)

| Column          |   Type   | Indexed | Nullable | FK  |     Default     | Description                                                        |
| :-------------- | :------: | :-----: | :------: | :-: | :-------------: | :----------------------------------------------------------------- |
| `key`           |   text   | unique  |          |     |                 | Key that can be used to get the corresponding Transformer subclass |
| `date_created`  | datetime |         |          |     |       now       |                                                                    |
| `date_modified` | datetime |         |          |     | now (on update) |                                                                    |

## Logs

### HarvestLog
Log entries to track the status of a specific harvester run.

| Column                  |   Type    | Indexed | Nullable | FK  |     Default     | Description                                                                                                   |
| :---------------------- | :-------: | :-----: | :------: | :-: | :-------------: | :------------------------------------------------------------------------------------------------------------ |
| `ingest_config_id`      |    int    |    ✓    |          |  ✓  |                 | IngestConfig for this harvester run                                                                           |
| `start_date`            | datetime  |    ✓    |          |     |                 | Beginning of the date range to harvest                                                                        |
| `end_date`              | datetime  |    ✓    |          |     |                 | End of the date range to harvest                                                                              |
| `status`                | enum(int) |    ✓    |          |     |     CREATED     | Status of the harvester run, one of {CREATED, STARTED, SPLIT, SUCCEEDED, FAILED, RESCHEDULED}                 |
| `error`                 |   text    |         |          |     |       ""        | A custom error message or traceback describing why this job failed                                            |
| `completions`           |    int    |         |          |     |        0        | The number of times `status` has been set to SUCCEEDED                                                        |
| `date_started`          | datetime  |         |          |     |                 | Datetime `status` was last set to STARTED                                                                     |
| `date_created`          | datetime  |         |          |     |       now       | Datetime this row was created                                                                                 |
| `date_modified`         | datetime  |         |          |     | now (on update) | Datetime this row was last modified                                                                           |
| `share_version`         |   text    |         |          |     |     UNKNOWN     | The commitish at the time this job was last run                                                               |
| `harvester_version`     |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the harvester, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010')      |
| `ingest_config_version` |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the `IngestConfig`, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010') |

#### Other indices
* `ingest_config_id`, `harvester_version`, `start_date`, `end_date` (unique)

#### Notes
* In the future, jobs may attempt to optimize themselves by searching for jobs that have already harvested a section of it required date range
* In the future, jobs may be merged together if they have overlapping date ranges to save on table space


### HarvestLogRawDatum
Through-table that links a `RawDatum` to a `HarvestLog`. (Let Django generate this)

| Column           | Type | Indexed | Nullable | FK  | Default | Description |
| :--------------- | :--: | :-----: | :------: | :-: | :-----: | :---------- |
| `harvest_log_id` | int  |    ✓    |          |  ✓  |         |             |
| `rawdatum_id`    | int  |    ✓    |          |  ✓  |         |             |


### IngestLog
Log entries to track the status of an ingest task

| Column                  |   Type    | Indexed | Nullable | FK  |     Default     | Description                                                                                                   |
| :---------------------- | :-------: | :-----: | :------: | :-: | :-------------: | :------------------------------------------------------------------------------------------------------------ |
| `raw_datum_id`          |    int    |    ✓    |          |  ✓  |                 | RawDatum to be transformed                                                                                    |
| `ingest_config_id`      |    int    |    ✓    |          |  ✓  |                 | IngestConfig used                                                                                             |
| `status`                | enum(int) |    ✓    |          |     |     CREATED     | Status of the transformer run, one of {CREATED, STARTED, SUCCEEDED, FAILED, RESCHEDULED}                      |
| `error`                 |   text    |         |          |     |       ""        | A custom error message or traceback describing why this job failed                                            |
| `completions`           |    int    |         |          |     |        0        | The number of times `status` has been set to SUCCEEDED                                                        |
| `date_started`          | datetime  |         |    ✓     |     |                 | Datetime `status` was last set to STARTED                                                                     |
| `date_created`          | datetime  |         |          |     |       now       | Datetime this row was created                                                                                 |
| `date_modified`         | datetime  |         |          |     | now (on update) | Datetime this row was last modified                                                                           |
| `share_version`         |   text    |         |          |     |     UNKNOWN     | The commitish at the time this job was last run                                                               |
| `transformer_version`   |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the transformer, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010')    |
| `regulator_version`     |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the regulator, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010')      |
| `consolidator_version`  |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the consolidator, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010')   |
| `ingest_config_version` |   text    |    ✓    |          |     |   000.000.000   | Semantic version of the `IngestConfig`, with each segment padded to 3 digits (e.g. '1.2.10' => '001.002.010') |

#### Other indices
* `raw_id`, `transformer_version` (unique)

#### Notes
* `regulator_version` and `consolidator_version` will be mutable. Whenever the regulator or consolidator version gets bumped existing jobs should be updated.