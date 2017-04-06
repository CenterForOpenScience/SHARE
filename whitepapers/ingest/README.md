# Ingest Pipeline

* The [Transformer](./Transformer.md) creates a [Graph](./Graph.md) from the raw data for a given SUID.
* The [Regulator](./Regulator.md) cleans the transformed [Graph](./Graph.md) and validates it against a standard set of criteria.
* The [Consolidator](./Consolidator.md) updates the SUID's existing StateGraph to match the regulated [Graph](./Graph.md)


