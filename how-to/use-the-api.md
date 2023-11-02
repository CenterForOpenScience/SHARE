# How to use the API

(see [openapi docs](/trove/openapi.ui) for detail)

## Sample and search for index-cards

`GET /trove/index-card-search`: search index-cards

`GET /trove/index-value-search`: search values for specific properties on index-cards

## Posting index-cards
> NOTE: currently used only by other COS projects, not yet for public use

`POST /trove/ingest?focus_iri=...&record_identifier=...`: 

currently supports only `Content-Type: text/turtle`

## Deleting index-cards

`DELETE /trove/ingest?record_identifier=...`: request 


## Harvesting metadata records in bulk

`/oaipmh` -- an implementation of the Open Access Initiative's [Protocol for Metadata Harvesting](https://www.openarchives.org/OAI/openarchivesprotocol.html), an open standard for harvesting metadata
from open repositories. You can use this to list metadata in bulk, or query by a few simple
parameters (date range or source).

