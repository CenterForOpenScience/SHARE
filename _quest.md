# es8

## TODO
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

### admin controls
view info about indexes (including current but not-yet-created)

specific-index actions:
- pls_setup (if index not created)
- pls_organize_backfill (should normally fill automatically)
- pls_open_for_searching (when fill is done)
- pls_delete (when moved on to a new version)



## DONE
