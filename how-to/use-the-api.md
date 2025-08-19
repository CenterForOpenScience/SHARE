# how to use the api

## searching and browsing

`GET /trove/index-card-search`: search for cards that identify and describe things

`GET /trove/index-value-search`: search for values (like identifiers) used on cards, which you can use in card-searches

`GET /trove/browse?iri=...`: inquire about a thing you have already identified

(see [openapi docs](/trove/docs/openapi.html) for detail and available parameters)


### Posting index-cards
> NOTE: currently used only by other COS projects, not yet for public use, authorization required

`POST /trove/ingest?focus_iri=...`: 

currently supports only `Content-Type: text/turtle`

query params:
- `focus_iri` (required): full iri of the focus resource, exactly as used in the request body
- `record_identifier`: a source-specific identifier for the metadata record (if omitted, uses `focus_iri`) -- sending another record with the same `record_identifier` is considered a full update (only the most recent is used)
- `nonurgent`: if present (regardless of value), ingestion may be given a lower priority -- recommended for bulk or background operations
- `is_supplementary`: if present (regardless of value), this record's metadata will be added to all pre-existing index-cards from the same user with the same `focus_iri` (if any), but will not get an index-card of its own nor affect the last-updated timestamp (e.g. in OAI-PMH) of the index-cards it supplements
    - note: supplementary records must have a different `record_identifier` from the primary records for the same focus
- `expiration_date`: optional date (in format `YYYY-MM-DD`) when the record is no longer valid and should be removed

## Deleting index-cards

`DELETE /trove/ingest?record_identifier=...`: request 


## Harvesting metadata records in bulk

`/oaipmh` -- an implementation of the Open Access Initiative's [Protocol for Metadata Harvesting](https://www.openarchives.org/OAI/openarchivesprotocol.html), an open standard for harvesting metadata
from open repositories. You can use this to list metadata in bulk, or query by a few simple
parameters (date range or source).
