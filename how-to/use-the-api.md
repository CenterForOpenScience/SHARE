# How to use the API

(see [openapi docs](/trove/docs/openapi.html) for detail)

## Sample and search for index-cards

`GET /trove/index-card-search`: search index-cards

`GET /trove/index-value-search`: search values for specific properties on index-cards

## Posting index-cards
> NOTE: currently used only by other COS projects, not yet for public use, authorization required

`POST /trove/ingest?focus_iri=...&record_identifier=...`: 

currently supports only `Content-Type: text/turtle`

query params:
- `focus_iri` (required): full iri of the focus resource, exactly as used in the request body
- `record_identifier` (required): a source-specific identifier for the metadata record (no format restrictions) -- sending another record with the same `record_identifier` is considered a full update (only the most recent is used)
- `nonurgent`: if present (regardless of value), ingestion may be given a lower priority -- recommended for bulk or background operations
- `is_supplementary`: if present (regardless of value), this record's metadata will be added to all pre-existing index-cards from the same user with the same `focus_iri` (if any), but will not get an index-card of its own nor affect the last-updated timestamp (e.g. in OAI-PMH) of the index-cards it supplements

## Deleting index-cards

`DELETE /trove/ingest?record_identifier=...`: request 


## Harvesting metadata records in bulk

`/oaipmh` -- an implementation of the Open Access Initiative's [Protocol for Metadata Harvesting](https://www.openarchives.org/OAI/openarchivesprotocol.html), an open standard for harvesting metadata
from open repositories. You can use this to list metadata in bulk, or query by a few simple
parameters (date range or source).

