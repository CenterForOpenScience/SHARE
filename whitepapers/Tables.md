# SQL Tables

## Template

### {ModelName}
{Description}

| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| | | ✓ | ✓ | ✓ | | |

#### Other indices
* `{column_name}`, `{column_name}`, ... [(unique)]
* ...

## Data

### SourceUniqueIdentifier (SUID)
Identifier for a specific document from a specific source.

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `source_doc_id` | text |  |  |  |  | Identifier given to the document by the source |
| `ingest_config_id` | int |  |  | ✓ |  | IngestConfig used to ingest the document |

#### Other indices
* `source_doc_id`, `ingest_config_id` (unique)

### RawData
Raw data, exactly as it was given to SHARE.

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `suid_id` | int |  |  | ✓ | | SUID for this datum |
| `data` | text |  |  |  | | The raw data itself (typically JSON or XML string) |
| `sha256` | text | unique |  |  | | SHA-256 hash of `data` |
| `date_seen` | datetime |  |  |  | now (every update) | The last time this exact data was harvested |
| `date_harvested` | datetime |  |  |  | now (on insert) | The first time this exact data was harvested |

## Ingest Configuration

### IngestConfig
Describes one way to harvest metadata from a Source, and how to transform the result.

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `source_id` | int |  |  | ✓ | | Source to harvest from |
| `base_url` | text |  |  |  | | URL of the API or endpoint where the metadata is available |
| `earliest_date` | date |  | ✓ |  | | Earliest date with available data |
| `rate_limit_allowance` | int |  |  |  | 5 | Number of requests allowed every `rate_limit_period` seconds |
| `rate_limit_period` | int |  |  |  | 1 | Number of seconds for every `rate_limit_allowance` requests |
| `harvester_id` | int |  |  | ✓ | | Harvester to use |
| `harvester_kwargs` | jsonb |  | ✓ |  | | JSON object passed to the harvester as kwargs |
| `transformer_id` | int |  |  | ✓ | | Transformer to use |
| `transformer_kwargs` | jsonb |  | ✓ |  | | JSON object passed to the transformer as kwargs, along with the harvested raw data |
| `disabled` | bool |  |  |  | False | True if this ingest config should not be run automatically |

### Source
A Source is a place metadata comes from.

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `name` | text | unique |  |  | | Short name |
| `long_title` | text | unique |  |  | | Full, human-friendly name |
| `home_page` | text |  | ✓ |  | | URL |
| `icon` | image |  | ✓ |  | | Recognizable icon for the source |
| `user_id` | int |  |  | ✓ | | User with permission to submit data as this source (TODO: replace with django permissions stuff) |

### Harvester
Each row corresponds to a Harvester implementation in python. (TODO: describe those somewhere)

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `key` | text | unique |  |  | | Key that can be used to get the corresponding Harvester subclass |
| `date_created` | datetime |  |  |  | now (on insert) | |

### Transformer
Each row corresponds to a Transformer implementation in python. (TODO: describe those somewhere)

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `key` | text | unique |  |  | | Key that can be used to get the corresponding Transformer subclass |
| `date_created` | datetime |  |  |  | now (on insert) | |

## Logs

### HarvestLog
Log entries to track the status of a specific harvester run.

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `ingest_config_id` | int |  |  | ✓ | | IngestConfig for this harvester run |
| `harvester_version` | text |  |  |  | | Current version of the harvester in format 'x.x.x' |
| `start_date` | datetime |  |  |  | | Beginning of the date range to harvest |
| `end_date` | datetime |  |  |  | | End of the date range to harvest |
| `started` | datetime |  |  |  | | Time `status` was set to STARTED |
| `status` | text |  |  |  | INITIAL | Status of the harvester run, one of {INITIAL, STARTED, SPLIT, SUCCEEDED, FAILED} |

#### Other indices
* `ingest_config_id`, `harvester_version`, `start_date`, `end_date` (unique)

### TransformLog
Log entries to track the status of a transform task

#### Columns
| Column | Type | Indexed | Nullable | FK | Default | Description |
|:-------|:----:|:-------:|:---------|:--:|:-------:|:------------|
| `raw_id` | int |  |  | ✓ | | RawData to be transformed |
| `ingest_config_id` | int |  |  | ✓ | | IngestConfig used |
| `transformer_version` | text |  |  |  | | Current version of the transformer in format 'x.x.x' |
| `started` | datetime |  |  |  | | Time `status` was set to STARTED |
| `status` | text |  |  |  | INITIAL | Status of the transform task, one of {INITIAL, STARTED, RESCHEDULED, SUCCEEDED, FAILED} |

#### Other indices
* `raw_id`, `transformer_version` (unique)
