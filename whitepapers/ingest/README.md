# Ingest Pipeline

* The [Transformer](./Transformer.md) creates a [StateGraph](./Graph.md) from the raw data for a given SUID.
* The [Regulator](./Regulator.md) cleans the transformed [StateGraph](./Graph.md) and validates it against a standard set of criteria.
* The [Consolidator](./Consolidator.md) updates the SUID's existing states to match the regulated [StateGraph](./Graph.md)


