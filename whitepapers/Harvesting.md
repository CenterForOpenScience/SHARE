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
TODO


#### Notes
* In the future, jobs may attempt to optimize themselves by searching for jobs that have already harvested a section of it required date range
* In the future, jobs may be merged together if they have overlapping date ranges to save on table space


## FAQ
TODO
