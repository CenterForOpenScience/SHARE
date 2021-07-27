# Architecture of SHARE/Trove

This document is a starting point and reference to familiarize yourself with this codebase.

## Bird's eye view
In short, SHARE/Trove takes metadata records (in any supported input format),
ingests them, and makes them available in any supported output format.
```
            ┌───────────────────────────────────────────┐
            │                  Ingest                   │
            │                                  ┌──────┐ │
            │ ┌─────────────────────────┐   ┌──►Format├─┼────┐
            │ │        Normalize        │   │  └──────┘ │    │
            │ │                         │   │           │    ▼
┌───────┐   │ │ ┌─────────┐  ┌────────┐ │   │  ┌──────┐ │    save as
│Harvest├─┬─┼─┼─►Transform├──►Regulate├─┼─┬─┼──►Format├─┼─┬─►FormattedMetadataRecord
└───────┘ │ │ │ └─────────┘  └────────┘ │ │ │  └──────┘ │ │
          │ │ │                         │ │ .           │ │  ┌───────┐
          │ │ └─────────────────────────┘ │ .           │ └──►Indexer│
          │ │                             │ .           │    └───────┘
          │ └─────────────────────────────┼─────────────┘  some formats also
          │                               │                indexed separately
          ▼                               ▼
        save as                         save as
        RawDatum                        NormalizedData
```

## Code map

A brief look at important areas of code as they happen to exist now.

### Static configuration

`share/schema/` describes the "normalized" metadata schema/format that all
metadata records are converted into when ingested.

`share/sources/` describes a starting set of metadata sources that the system
could harvest metadata from -- these will be put in the database and can be
updated or added to over time.

`project/settings.py` describes system-level settings which can be set by
environment variables (and their default values), as well as settings
which cannot.

`share/models/` describes the data layer using the [Django](https://www.djangoproject.com/) ORM.

`share/subjects.yaml` describes the "central taxonomy" of subjects allowed
in `Subject.name` fields of `NormalizedData`.

### Harvest and ingest

`share/harvest/` and `share/harvesters/` describe how metadata records
are pulled from other metadata repositories.

`share/transform/` and `share/transformers/` describe how raw data (possibly
in any format) are transformed to the "normalized" schema.

`share/regulate/` describes rules which are applied to every normalized datum,
regardless where or what format it originally come from.

`share/metadata_formats/` describes how a normalized datum can be formatted
into any supported output format.

`share/tasks/` runs the harvest/ingest pipeline and stores each task's status
(including debugging info, if errored) as a `HarvestJob` or `IngestJob`.

### Outward-facing views

`share/search/` describes how the search indexes are structured, managed, and
updated when new metadata records are introduced -- this provides a view for
discovering items based on whatever search criteria.

`share/oaipmh/` describes the [OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html)
view for harvesting metadata from SHARE/Trove in bulk.

`api/` describes a mostly REST-ful API that's useful for inspecting records for
a specific item of interest.

### Internals

`share/admin/` is a Django-app for administrative access to the SHARE database
and pipeline logs

`osf_oauth2_adapter/` is a Django app to support logging in to SHARE via OSF

### Testing

`tests/` are tests.

## Cross-cutting concerns

### Immutable metadata

Metadata records at all stages of the pipeline (`RawDatum`, `NormalizedData`,
`FormattedMetadataRecord`) should be considered immutable -- any updates 
result in a new record being created, not an old record being altered.

Multiple records which describe the same item/object are grouped by a
"source-unique identifier" or "suid" -- essentially a two-tuple
`(source, identifier)` that uniquely and persistently identifies an item in
the source repository. In most outward-facing views, default to showing only
the most recent record for each suid.

## Why this?
inspired by [this writeup](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html)
and [this example architecture document](https://github.com/rust-analyzer/rust-analyzer/blob/d7c99931d05e3723d878bea5dc26766791fa4e69/docs/dev/architecture.md)
