# es8

## TODO
### support multiple elastic clusters
perform all elastic operations thru one of two interfaces:
* share.search.DaemonMessage (across all indexes/clusters)
* share.search.IndexSetup (for a specific index)

share.search.IndexSetup knows of version- or cluster-specific features

share.search.daemon doesn't understand the difference,
                    knows only the common IndexSetup interface
                    acts on only a handful of iris,

use different elasticsearch client libraries for different versions

### add elasticsearch8 to local docker-compose.yml
get tests running across all clusters

### add elasticsearch8 to staging
however that's done

### add elasticsearch8 to production

## DONE
