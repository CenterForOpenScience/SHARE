# SQL Tables



## Pipeline configuration

### Source
A Source is a place metadata comes from.

#### Columns
* `name` -- Short, unique string
* `long_title` -- full, human-friendly name
* `home_page` -- URL
* `icon` -- 
* `user_id` -- PK of the user with permission to submit data as this source (TODO: replace with django permissions stuff)

### Harvester

#### Columns
* `key` -- Unique key that can be used to get the corresponding Harvester subclass
* `date_created` --

### Transformer

#### Columns
* `key` -- Unique key that can be used to get the corresponding Transformer subclass
* `date_created` --

### IngestConfig
Describes one way to harvest metadata from a Source, and how to transform the result.

#### Columns
* `source_id` -- PK of the source
* `base_url` -- URL of the API/endpoint where the metadata is available
* `earliest_date` -- Earliest date with available data (nullable)
* `rate_limit` -- Rate limit for network requests. Defaults to `None` (Unlimited)
* `harvester_id` -- PK of the harvester to use
* `harvester_kwargs` -- JSON object passed to the harvester as kwargs
* `transformer_id` -- PK of the transformer to use
* `transformer_kwargs` -- JSON object passed to the transformer as kwargs, along with the harvested raw data
* `disabled` -- Boolean
