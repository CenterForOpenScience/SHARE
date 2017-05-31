# Single-State Objects [NOT IMPLEMENTED]

## Overview

### Why?
Services built on SHARE deserve a stable foundation.
Disambiguating and merging objects are the most difficult problems in SHARE, and are not yet reliable.
The single-source API would guarantee that a source’s data in SHARE will not change unless that same source provides an update.
This would resolve most of the issues OSF Preprints has had using SHARE for discovery.
Curation associates could see exactly how the Transformer and Regulator interpret their data.

### What?
Take a step back from trying to solve everything at once.
Store transformed and regulated data in the SHARE schema, without trying to merge data from different sources together.
For each source, provide a view on the SHARE dataset with the illusion that no other source exists.

The existing API and search index for multi-source objects should be considered relatively unstable for the time being, and primarily intended for manual exploration and discovery.

## Requirements
Must be able to:
* Query the elastic index for data from a source.
* Use the API to fetch the version of a work provided by a source, in the SHARE schema.
* Guarantee that single-source data will not change unless new data is provided by that source (or the SHARE ingest pipeline is updated)
* View previous single-source versions of a given work

## Implementation

### Models
* (maybe) Define SHARE schema in some other format, create models based on it
    * YAML? XSD? Abstract models?
    * Define all types and fields from the Data Dictionary
        * CreativeWork
        * Agent
        * AgentRelation
        * WorkRelation
        * AgentWorkRelation
        * WorkIdentifier
        * AgentIdentifier
        * Tag
        * Award
        * ThroughTags
        * ThroughSubjects
        * ThroughContributor
        * ThroughAwards
        * ExtraData
    * Use as base classes for all models that store data in the SHARE schema
        * multi-source tables (existing)
        * multi-source version tables (existing)
        * single-source tables (new)
        * single-source merged tables (new)

* For each concrete SHARE type:
    * Unmerged single-source (US) model
        * Allows getting full graph for a SUID, unsullied by other SUIDs from the same source
        * `suid` field: SUID that was ingested to yield this object
    * Merged single-source (MS) model
        * Agents, related works, etc. from the same source (all source configs) merged together
        * Built from US objects
        * For each source, provides a view on the database with the illusion no other source exists
        * `suids` field: m2m to SUIDs that contributed to this object
    * Merged multi-source (MM) model
        * Existing SHARE tables
        * At first, leave the existing pipeline (disambiguator, changesets, etc.) unchanged
        * Eventually, build MM objects from MS objects

### Ingest Pipeline
When saving a new NormalizedData for a given SUID:
* Update US graph
    * Try to match as many normalized nodes as possible to existing US objects with the same SUID
        * Match works on identifier URI
        * Match agents on identifier URI or on cited name on related works
    * Update matching US objects with the new data
        * Ensure `date_modified` is not updated if no changes
    * Create US objects for nodes that don't match
    * Delete existing US objects from this SUID which don't match a node in the newly ingested data
* Update MS graph
    * Disambiguate against MS objects from the same source
    * Update matching MS objects, delete unmatched, create missing
* Update MM graph
    * Leave existing ingest pipeline intact for now
    * Eventually plan to build MM objects from MS objects

### Migration
* Create tables required for new models
* Copy data into new tables
    * Option 1: Save the most recent NormalizedData for each SUID as a set of single-state objects
    * Option 2: Reingest the most recent RawData for each SUID

### JSON API
TODO

### Search Index
Each source has its own elasticsearch index, in addition to the existing aggregate index.

### UI
TODO
