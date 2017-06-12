# SQL Tables

## Data

### SourceUniqueIdentifier (SUID)
Identifier for a specific document from a specific source.

| Column             | Type | Indexed | Nullable | FK  | Default | Description                                    |
| :----------------- | :--: | :-----: | :------: | :-: | :-----: | :--------------------------------------------- |
| `identifier`       | text |         |          |     |         | Identifier given to the document by the source |
| `source_config_id` | int  |         |          |  ✓  |         | SourceConfig used to harvest and ingest the document |

#### Other indices
* `identifier`, `source_config_id` (unique)

### RawDatum
A piece of raw data, exactly as it was given to SHARE.

| Column         | Type | Indexed | Nullable | FK  | Default | Description                                                        |
| :------------- | :--: | :-----: | :------: | :-: | :-----: | :----------------------------------------------------------------- |
| `suid_id`      | int  |    ✓    |          |  ✓  |         | SUID for this datum                                                |
| `datum`        | text |         |          |     |         | The raw datum itself (typically JSON or XML string)                |
| `sha256`       | text |         |          |     |         | SHA-256 hash of `data`                                             |
| `harvest_jobs` | m2m  |         |          |     |         | List of HarvestJobs for harvester runs that found this exact datum |
| `ingest_jobs`  | m2m  |         |          |     |         | List of IngestJobs that ingested this datum                        |

#### Other indices
* `suid_id`, `sha256` (unique)

## Source Configuration

### SourceConfig
Describes one way to harvest metadata from a Source, and how to transform the result.

| Column                 | Type  | Indexed | Nullable | FK  | Default | Description                                                                        |
| :--------------------- | :---: | :-----: | :------: | :-: | :-----: | :--------------------------------------------------------------------------------- |
| `source_id`            |  int  |    ✓    |          |  ✓  |         | Source to harvest from                                                             |
| `base_url`             | text  |         |    ✓     |     |         | URL of the API or endpoint where the metadata is available                         |
| `earliest_date`        | date  |         |    ✓     |     |         | Earliest date with available data                                                  |
| `rate_limit_allowance` |  int  |         |          |     |    5    | Number of requests allowed every `rate_limit_period` seconds                       |
| `rate_limit_period`    |  int  |         |          |     |    1    | Number of seconds for every `rate_limit_allowance` requests                        |
| `harvester_id`         |  int  |    ✓    |    ✓     |  ✓  |         | Harvester to use                                                                   |
| `harvester_kwargs`     | jsonb |         |    ✓     |     |         | JSON object passed to the harvester as kwargs                                      |
| `transformer_id`       |  int  |    ✓    |    ✓     |  ✓  |         | Transformer to use                                                                 |
| `transformer_kwargs`   | jsonb |         |    ✓     |     |         | JSON object passed to the transformer as kwargs, along with the harvested raw data |
| `disabled`             | bool  |         |          |     |  False  | True if this source config should not be run automatically                         |
| `version`              |  int  |         |          |     |    0    | Version of this source config                                                      |

### Source
A Source is a place metadata comes from.

| Column       | Type  | Indexed | Nullable | FK  | Default | Description                                                                                      |
| :----------- | :---: | :-----: | :------: | :-: | :-----: | :----------------------------------------------------------------------------------------------- |
| `name`       | text  | unique  |          |     |         | Short name                                                                                       |
| `long_title` | text  | unique  |          |     |         | Full, human-friendly name                                                                        |
| `home_page`  | text  |         |    ✓     |     |         | URL                                                                                              |
| `icon`       | image |         |    ✓     |     |         | Recognizable icon for the source                                                                 |
| `user_id`    |  int  |    ✓    |          |  ✓  |         | User with permission to submit data as this source (TODO: replace with django permissions stuff) |

### Harvester
Each row corresponds to a Harvester implementation in python.

| Column          |   Type   | Indexed | Nullable | FK  |     Default     | Description                                                      |
| :-------------- | :------: | :-----: | :------: | :-: | :-------------: | :--------------------------------------------------------------- |
| `key`           |   text   | unique  |          |     |                 | Key that can be used to get the corresponding Harvester subclass |
| `date_created`  | datetime |         |          |     |       now       |                                                                  |
| `date_modified` | datetime |         |          |     | now (on update) |                                                                  |

### Transformer
Each row corresponds to a Transformer implementation in python.

| Column          |   Type   | Indexed | Nullable | FK  |     Default     | Description                                                        |
| :-------------- | :------: | :-----: | :------: | :-: | :-------------: | :----------------------------------------------------------------- |
| `key`           |   text   | unique  |          |     |                 | Key that can be used to get the corresponding Transformer subclass |
| `date_created`  | datetime |         |          |     |       now       |                                                                    |
| `date_modified` | datetime |         |          |     | now (on update) |                                                                    |

## Jobs

### HarvestJob
Job entries to track the status of a specific harvester run.

| Column                  |   Type    | Indexed | Nullable | FK  |     Default     | Description                                                                                                   |
| :---------------------- | :-------: | :-----: | :------: | :-: | :-------------: | :------------------------------------------------------------------------------------------------------------ |
| `task_id`               |   uuid    |         |    ✓     |     |                 | UUID of the celery task running the harvester                                                                 |
| `status`                | enum(int) |    ✓    |          |     |     created     | Status of the harvester run, one of {created, started, failed, succeeded, rescheduled, forced, skipped, retried} |
| `context`               |   text    |         |          |     |       ""        | A custom message or traceback describing why this job failed or was skipped                                   |
| `completions`           |    int    |         |          |     |        0        | The number of times `status` has been set to `succeeded`                                                        |
| `date_started`          | datetime  |         |    ✓     |     |                 | Datetime `status` was last set to `started`                                                                     |
| `date_created`          | datetime  |         |          |     |       now       | Datetime this row was created                                                                                 |
| `date_modified`         | datetime  |    ✓    |          |     | now (on update) | Datetime this row was last modified                                                                           |
| `source_config_id`      |    int    |    ✓    |          |  ✓  |                 | SourceConfig for this harvester run                                                                           |
| `share_version`         |   text    |         |          |     |     UNKNOWN     | The commitish at the time this job was last run                                                               |
| `source_config_version` |    int    |         |          |     |                 | Version of the `SourceConfig` on the last attempted run                                                       |
| `start_date`            |   date    |    ✓    |          |     |                 | Beginning of the date range to harvest                                                                        |
| `end_date`              |   date    |    ✓    |          |     |                 | End of the date range to harvest                                                                              |
| `harvester_version`     |    int    |         |          |     |                 | Version of the harvester on the last attempted run                                                            |

#### Other indices
* `source_config_id`, `start_date`, `end_date`, `harvester_version`, `source_config_version` (unique)


### IngestJob (NOT IMPLEMENTED)
Job entries to track the status of an ingest task

| Column                  |   Type    | Indexed | Nullable | FK  |     Default     | Description                                                                                                   |
| :---------------------- | :-------: | :-----: | :------: | :-: | :-------------: | :------------------------------------------------------------------------------------------------------------ |
| `task_id`               |   uuid    |         |    ✓     |     |                 | UUID of the celery task running the harvester                                                                 |
| `status`                | enum(int) |    ✓    |          |     |     created     | Status of the harvester run, one of {created, started, failed, succeeded, rescheduled, forced, skipped, retried} |
| `context`               |   text    |         |          |     |       ""        | A custom message or traceback describing why this job failed or was skipped                                   |
| `completions`           |    int    |         |          |     |        0        | The number of times `status` has been set to `succeeded`                                                        |
| `date_started`          | datetime  |         |    ✓     |     |                 | Datetime `status` was last set to `started`                                                                     |
| `date_created`          | datetime  |         |          |     |       now       | Datetime this row was created                                                                                 |
| `date_modified`         | datetime  |    ✓    |          |     | now (on update) | Datetime this row was last modified                                                                           |
| `share_version`         |   text    |         |          |     |     UNKNOWN     | The commitish at the time this job was last run                                                               |
| `suid_id`               |    int    |    ✓    |          |  ✓  |                 | SUID of the document to ingest                                                                                |
| `latest_raw_id`         |    int    |    ✓    |          |  ✓  |                 | The latest (or only) RawDatum this job will (or did) ingest                                                   |
| `source_config_version` |    int    |         |          |     |                 | Version of the SUID's `SourceConfig` on the last attempted run                                                |
| `transformer_version`   |    int    |         |          |     |                 | Version of the Transformer    |
| `regulator_version`     |    int    |         |          |     |                 | Version of the Regulator      |
| `consolidator_version`  |    int    |         |          |     |                 | Version of the Consolidator   |
| `transformed_data`      |   text    |         |    ✓     |     |                 | Serialized output from the Transformer                                                                        |
| `regulator_log`         |   text    |         |    ✓     |     |                 | Human-readable summary of modifications made by the Regulator, with a reason for each                         |
| `regulated_data`        |   text    |         |    ✓     |     |                 | Serialized output from the Regulator                                                                          |

#### Other indices
* `suid_id`, `latest_raw_id`, `source_config_version`, `transformer_version`, `regulator_version`, `consolidator_version` (unique)

#### Notes
* `regulator_version` and `consolidator_version` will be mutable. Whenever the regulator or consolidator version gets bumped existing jobs should be updated.


## Template

### {ModelName}
{Description}

| Column | Type | Indexed | Nullable | FK  | Default | Description |
| :----- | :--: | :-----: | :------: | :-: | :-----: | :---------- |
|        |      |    ✓    |    ✓     |  ✓  |         |             |

#### Other indices
* `{column_name}`, `{column_name}`, ... [(unique)]
* ...
