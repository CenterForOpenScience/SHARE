# es8

## TODO
- document process for new/updated index strategies
- unit tests for IndexStrategy
- unit tests for IndexMessenger
- backcompat: search response `hits.total` 


## DONE
### support multiple elastic clusters
perform all elastic operations thru one of two interfaces:
* share.search.IndexStrategy
    * for operations on a specific index
    * knows of version- or cluster-specific features
    * encapsulates elasticsearch client library
    * handles index create/delete/update/query/fill
* share.search.IndexMessenger
    * for operations across all/many indexes/clusters
    * uses the common IndexStrategy interface and share.search.messages

### local elastic8
add to docker-compose.yml

add/use ELASTICSEARCH8_URL environment var

add sharev2_elastic8 copy of existing index

add query param to existing search api to use elastic8

- remove direct-by-url elasticsearch access (go via IndexStrategy instead)
    - rss/atom feed

### admin controls
view info about indexes (including current but not-yet-created)

specific-index actions:
- pls_create
- pls_start_keeping_live
- pls_start_backfill
- pls_mark_backfill_complete
- pls_make_default_for_searching
- pls_stop_keeping_live
- pls_delete

- admin: confirm index refill/delete
- admin: easy-update default index strategy for `/api/v2/search/...` and `/api/v2/feeds/...`
