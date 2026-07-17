# how to use the admin site

shtrove has a [django admin site](https://docs.djangoproject.com/en/stable/ref/contrib/admin/)
at `/admin/` that can be used for interacting with the database and managing search indexes
-- this document describes how to use the admin site for some common tasks

## prerequisite: creating an admin user
an admin user is automatically created as part of initial setup (database migrations)
when the `SHARE_ADMIN_PASSWORD` environment variable (or django setting) is non-empty,
with username from `SHARE_ADMIN_USERNAME` (default "admin")

in local development, when [DEBUG](https://docs.djangoproject.com/en/stable/ref/settings/#debug)
is true and you shouldn't have any sensitive data, `SHARE_ADMIN_PASSWORD` defaults to "password"

other `ShareUser` instances (perhaps created by logging in with OSF OAuth, below) can be granted
admin-site permissions -- find them at `/admin/share/shareuser/`, set "Staff status"
(`is_staff`) to give access to the admin site, and either select specific permissions
or set "Superuser status" (`is_superuser`) to give all permissions.

### with OSF account
when set up with OSF, you can also click "login with osf" (or go to `/accounts/osf/login/`)
to login with an OSF account -- this will create a `ShareUser` instance that can be granted
admin-site permissions, as above

## how to view metadata about a specific resource
to find metadata about a specific resource, use the `Indexcard` model as a starting point -- click
on "Indexcards" in the "TROVE" section of `/admin/` (or go to `/admin/trove/indexcard/` directly)
and search by either indexcard uuid or source-unique identifier (e.g. OSF id)

an Indexcard's detail view has links to:
- current version of core metadata ("latest resource description")
- past versions of core metadata ("archived description set")
- current supplementary metadata ("supplementary description set")
- different serializations of current metadata ("derived indexcard set")

if an Indexcard has been marked deleted, its "latest" and "derived" data will be removed
but "archived" will remain

## how to view index statuses
click on the "elasticsearch indexes" link in the admin-site header (or go to `/admin/search-indexes`)
to see the current status of all configured index strategies, including their queues and indexes

for each available index strategy, this page provides:
- status of urgent and non-urgent queues
    - depth (count of enqueued messages)
    - approximate indexing rate over the past 30 seconds
- for the current version of this strategy:
    - backfill status (if any)
        - for manual tracking of backfill progress
        - click link to view/reset backfill status and error message, if any
    - lifecycle controls (each displayed only when safe to do):
        - setup (create indexes -- note only the current version can be set up)
        - start keeping live (receive new metadata updates)
        - start backfill (schedule task to enqueue indexer messages for all existing cards)
        - mark backfill complete (to be done manually, when queue clear)
        - make default for searching within this strategy (only when backfill marked complete)
        - delete -- must confirm by typing "really really"
    - status of each specific index within this strategy version:
        - key (short name within the strategy)
        - created date
        - kept-live state (whether it receives new metadata updates)
        - doc count (as of last index refresh), with direct link to view index
        - link to elasticsearch mappings
        - full index name
- for each prior version of this same strategy (that still has existing indexes):
    - unique checksum of index mappings/settings
    - lifecycle controls (each displayed only when safe to do):
        - start keeping live (receive new metadata updates)
        - make default for searching within this strategy (only when backfill marked complete)
        - delete (only when not default for searching) -- must confirm by typing "really really"
    - status of each specific index within this strategy version:
        - key (short name within the strategy)
        - created date
        - kept-live state (whether it receives new metadata updates)
        - doc count (as of last index refresh), with direct link to view index
        - link to elasticsearch mappings
        - full index name

see [how to wrangle index strategies](./wrangle-index-strategies.md) for more context

## how to diagnose ingestion problems

if something is missing from search:
1. does it have an Indexcard (see above for finding it)? if not:
    - requests to `/trove/ingest` are either failing or not being sent (check OSF task logs? or shtrove web-server errors?)
2. does the Indexcard have a `deleted` date? if so:
    - the source (OSF) apparently sent a DELETE request (check why?)
3. does the Indexcard have `DerivedIndexcard`s? if not:
    - `task__derive` may be failing (check for errors at `/admin/share/celerytaskresult/`)
    - ...or not running at all (check for a backup in `digestive_tract` queues, or problems with shtrove's `worker`)
4. is there a large queue depth at `/admin/search-indexes`? if so:
    - check shtrove's `indexer` logs for errors
5. if all above seems fine:
    - compare the search query to the metadata record -- any mismatched assumptions?
