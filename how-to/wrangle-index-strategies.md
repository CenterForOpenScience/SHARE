# how to wrangle index strategies
`IndexStrategy` exists to make it easy to index the same trove of metadata in multiple different
ways that may be compared, replaced, and improved over time

(for implementations, see `share.search.index_strategy`)

## strategy checksums (versions)
the version of an index strategy is identified by a checksum of the mappings and settings for
each of its indexes -- there can be only one "current" version of an index strategy, which
is statically defined in code, but there may be multiple "prior" versions that were created
from earlier code but which still exist in elasticsearch (and may still be used)

when a strategy version is "kept live", it will receive new metadata updates in the "current"
document format -- this means any new version of an existing index strategy must have a
back-compatible document structure to avoid breaking prior versions

## how to set up a new version of an index strategy
if you want to change things in a non-breaking way (like changing index settings, changing field
mappings without changing the source document, or adding new fields (without `dynamic: "strict"`)),
you can change the `IndexStrategy` subclass in-place to create a new "current" version of it

1. change the mappings/settings `IndexStrategy` subclass, making sure document structure is still back-compatible
2. update the `IndexStrategy` subclass's `CURRENT_STRATEGY_CHECKSUM` (easy way: follow the error message from trying to run a django service or command)
3. ensure all services are running up-to-date code (in local dev setup, restart `indexer`, `worker`, and `web`)
4. in the [shtrove admin site](./use-the-admin-site.md), use `/admin/search-indexes` to setup and backfill the new current version
5. use the trove api with `indexStrategy` query param (using the full `mystrategy__checksum...` identifier) to test/compare against the prior (default) version
6. when ready, use `/admin/search-indexes` to make the new version the default for searching and (when really really ready) to delete the prior version

## how to set up a new index strategy
if you want to change things in a breaking way (like incompatible document structure or a
major-version upgrade of elasticsearch) you should instead create a new index strategy

1. add an instance of your `IndexStrategy` subclass to `share.search.index_strategy._AvailableStrategies` with a unique shortname (this should someday be configurable in settings, but is currently hard-coded)
2. ensure all services are running up-to-date code (in local dev setup, restart `indexer`, `worker`, and `web`)
3. in the [shtrove admin site](./use-the-admin-site.md), use `/admin/search-indexes` to setup and backfill the current version of your new index strategy
4. use the api with `indexStrategy` query param to test/compare against other strategies
5. to update the default strategy for the trove search api (`/trove/index-card-search`, `/trove/index-value-search`), change the hard-coded default in `share.search.index_strategy.get_strategy_for_trovesearch` (this should also someday be configurable in settings (or admin site), but is not currently)
