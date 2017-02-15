# SQL Tables

## Template

### {ModelName}
{Description}

#### Columns
* `{column_name}` -- {description} ({datatype}, [unique,] [indexed,] [nullable,] [default={value},] [choices={choices],])
* ...

#### Multi-column indices
* `{column_name}`, `{column_name}`, ... [(unique)]
* ...

## Data

### SourceUniqueIdentifier (SUID)
Identifier for a specific document from a specific source.

#### Columns
* `source_doc_id` -- Identifier given to the document by the source (text)
* `ingest_config_id` -- PK of the IngestConfig used to ingest the document (int)

#### Multi-column indices
* `source_doc_id`, `ingest_config_id` (unique)

### RawData
Raw data, exactly as it was given to SHARE.

#### Columns
* `suid_id` -- PK of the SUID for this datum (int)
* `data` -- The raw data itself (text)
* `sha256` -- SHA-256 hash of `data` (text)
* `date_seen` -- The last time this exact data was harvested (datetime)
* `date_harvested` -- The first time this exact data was harvested (datetime)

## Ingest Configuration

### IngestConfig
Describes one way to harvest metadata from a Source, and how to transform the result.

#### Columns
* `source_id` -- PK of the source (int)
* `base_url` -- URL of the API/endpoint where the metadata is available (text)
* `earliest_date` -- Earliest date with available data (date, nullable)
* `rate_limit_allowance` -- Number of requests allowed every `rate_limit_period` seconds (positive int, default=5)
* `rate_limit_period` -- Number of seconds for every `rate_limit_allowance` requests (positive int, default=1)
* `harvester_id` -- PK of the harvester to use (int)
* `harvester_kwargs` -- JSON object passed to the harvester as kwargs (json, nullable)
* `transformer_id` -- PK of the transformer to use (int)
* `transformer_kwargs` -- JSON object passed to the transformer as kwargs, along with the harvested raw data (json, nullable)
* `disabled` -- True if this ingest config should not be run automatically (boolean)

### Source
A Source is a place metadata comes from.

#### Columns
* `name` -- Short name (text, unique)
* `long_title` -- Full, human-friendly name (text, unique)
* `home_page` -- URL (text, nullable)
* `icon` -- Icon for the source (image, nullable)
* `user_id` -- PK of the user with permission to submit data as this source (TODO: replace with django permissions stuff) (int)

### Harvester
Each row corresponds to a Harvester implementation in python. (TODO: describe those somewhere)

#### Columns
* `key` -- Key that can be used to get the corresponding Harvester subclass (text, unique)
* `date_created` -- Date created (datetime)

### Transformer
Each row corresponds to a Transformer implementation in python. (TODO: describe those somewhere)

#### Columns
* `key` -- Key that can be used to get the corresponding Transformer subclass (text, unique)
* `date_created` -- Date created (datetime)

## Logs

### HarvestLog
Log entries to track the status of a specific harvester run.

#### Columns
* `ingest_config_id` -- PK of the IngestConfig for this harvester run (int)
* `harvester_version` -- Current version of the harvester in format 'x.x.x' (text)
* `start_date` -- Beginning of the date range to harvest (datetime)
* `end_date` -- End of the date range to harvest (datetime)
* `started` -- Time this harvester run began (datetime)
* `status` -- Status of the harvester run (string, choices={INITIAL, STARTED, SPLIT, SUCCEEDED, FAILED}, default=INITIAL)

#### Multi-column indices
* `ingest_config_id`, `harvester_version`, `start_date`, `end_date` (unique)

### TransformLog
Log entries to track the status of a specific harvester run.

#### Columns
* `raw_id` -- PK of the RawData to be transformed (int)
* `ingest_config_id` -- PK of the IngestConfig (int)
* `transformer_version` -- Current version of the transformer in format 'x.x.x' (text)
* `started` -- Time this transform task began (datetime)
* `status` -- Status of the transform task (string, choices={INITIAL, STARTED, RESCHEDULED, SUCCEEDED, FAILED}, default=INITIAL)

#### Multi-column indices
* `raw_id`, `transformer_version` (unique)
