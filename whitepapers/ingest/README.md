# Ingest Pipeline

* The [Transformer](./Transformer.md) gathers the raw data for a given SUID and transforms it into a [MutableGraph](./Graph.md) object that roughly aligns with the current SHARE schema.
* The [Regulator](./Regulator.md) cleans the transformed [MutableGraph](./Graph.md) and validates it against the SHARE schema and other standard criteria.
* The [Consolidator](./Consolidator.md) updates the SUID's existing states to match the regulated [MutableGraph](./Graph.md)


