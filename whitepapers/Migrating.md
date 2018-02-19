# Migrating to the new system

* Normalized data will need to be copied to raw data over at somepoint
* Normalized data, Changes, ChangeSets will be dropped
* States will have to exist in parallel with Changes

1. Integrating SUIDs
2. Copy Normalized data to RawData
3. Start creating process logs for everything
4. Start creating states in parallel with changes
5. Implement Janitor tasks required to full populate states
6. Disambiguate states against the existing dataset
7. Disable changes workflow
8. Migrate the "Final Tables" to their new format
9. Enable all Janitor tasks
10. Drop all unused tables



(Special note: The @graph key can be sorted)

Logs for Create Delete Merge Split UnDelete
New States


## Integrating SUIDs
1. Create `Source`, `SourceConfig`, `Harvester`, `Transformer` models/tables
2. Populate `Source`s from `ShareUser`s that are robots
3. Populate `Harvester`, `Transformer`, and `SourceConfig` from existing django apps
4. Rename `RawData` -> `RawDatum` (This is done first for clarity)
5. Create `SourceUniqueIdentifier` model/table
6. Populate `SourceUniqueIdentifier`s from `RawData` using `provider_doc_id` and `app_label`

Migrated `RawData` will remain unascoiated with any `HarvestJobs`.
We'll rely on a combination of back-harvesting and Janitor tasks to slowly rediscover and log the `RawData`
