# Change Log

# [23.0.4] - 2023-05-05
- fix a typo

# [23.0.3] - 2023-05-05
- admin interface: allow re-ingesting all data for a source config
    (see "ingest" buttons at `/admin/share/sourceconfig/`)
- address possible cause of some backfill gaps
- fix logging errors

# [23.0.0] - 2023-05-03
- upgrade to python 3.11
- upgrade to elasticsearch 8
- add `share.search.index_strategy` to act as a slippery abstraction layer between search-engine backend and planned friendly search api
  - configure two index strategies (and make it easy to add more in the future):
    - `sharev2_elastic5`: the existing/legacy SHAREv2 search index as exists on elasticsearch5 and exposed via `/api/v2/search/creativeworks/_search`
    - `sharev2_elastic8`: a mirror/replacement for `sharev2_elastic5` with all the same `_source` docs (but possible incompatibilities for the existing pass-thru api)
- add a happy-path index-backfill workflow to the admin interface at `/admin/search-indexes`
  - when changing index-strategy settings/mappings/whatever, the "happy path" is to create, backfill, verify a new copy of the index; then switch which is used for searching, verify again, and finally delete the old index.
  - not intended to have the power of a full elasticsearch management interface -- just enough visibility to see whether things are going ok and where to start looking if something goes wrong
- for testing, support `indexStrategy` query param to `/api/v2/search/creativeworks/_search`, `/api/feeds/rss`, `/api/feeds/atom`
  - may request a configured strategy (e.g. `indexStrategy=sharev2_elastic8`) or a specific version of an index within a strategy (e.g. `indexStrategy=sharev2_elastic8__bcaa90e8fa8a772580040a8edbedb5f727202d1fca20866948bc0eb0e935e51f`)
- add `FeatureFlag` model, use it to switch default search strategy (`name="elastic_eight_default"`)

# [22.0.1] - 2022-08-29
- add `suid` value to `sharev2_elastic` index

# [22.0.0] - 2022-08-29
- easy additive elastic mapping changes
- add `osf_related_resource_types` field
- dockerfile updates

# [21.3.1] - 2021-07-28
- update raven

# [21.3.0] - 2021-07-28
- update and consolidate docs
- audit and upgrade all dependencies
- switch to github actions for tests/ci

# [21.2.2] - 2021-05-25
- fix: feeds should not break on null date_published

# [21.2.1] - 2021-05-25
- fix: oai_dc formatter breaks on deletions

# [21.2.0] - 2021-05-25
- big rend! remove many things:
  - concepts:
    - merging data from multiple sources together (aiming instead for a simple,
      robust repository of metadata records -- let's talk later/soon about how
      we might do merging well)
  - models:
    - `ShareObject` and all its descendents
    - `ShareObjectVersion` and all its descendents
    - `Change`
    - `ChangeSet`
    - `SubjectTaxonomy`
    - `UnusedCeleryProviderTask`
    - `UnusedCeleryTask`
  - api routes:
    - all auto-generated `ShareObject` routes (e.g. `/api/v2/creativeworks/`)
    - all `schema` routes (except the root `/api/v2/schema/`)
      - auto-generated schema routes (e.g. `/api/v2/schema/disputes/`)
      - work type hierarchy (`/api/v2/schema/creativeworks/hierarchy/`)
    - `/api/v2/graph/`
- admin features/improvements
  - add FormattedMetadataRecord admin
  - when investigating a problem, start by finding the suid and navigate
    relationships from there
  - add action to delete all FormattedMetadataRecords for some chosen suid(s)
    (good for spam control)

# [21.1.4] - 2021-05-17
- fix a 500 error at `/api/v2/`
- fix sending useful debugging info to sentry

# [21.1.3] - 2021-05-05
- make the oai-pmh feed respect switch-flipping

# [21.1.2] - 2021-05-05
- give an accurate `date_created` in sharev2_elastic formatter
- fix admin bug -- don't hide the search box
- add django-debug-toolbar to dev dependencies

# [21.1.1] - 2021-05-04
- tidy up some admin inefficiencies

# [21.1.0] - 2021-04-21
- expose a few models in read-only json:api, so the frontend can be useful given a suid
  - `/api/v2/formattedmetadatarecords/`
  - `/api/v2/sourceconfigs/`
  - `/api/v2/suids/`
- add new atom/rss feeds that get results from the new backcompat index
  - `/api/v2/feeds/atom/`
  - `/api/v2/feeds/rss/`
  - (old feeds now deprecated, will be gone with ShareObject)

# [21.0.8] - 2021-04-01
- add `--pls-reingest` arg to format_metadata_records command

# [21.0.7] - 2021-04-01
- fix: facility != funder (in gov.clinicaltrials transformer)

# [21.0.6] - 2021-04-01
- remove feature: oai_dc formatter no longer puts first author last
- add utility: `share.util.names.get_related_agent_name` for consistently
  getting an agent name from an "agent-work relation" node 
  - if missing both `cited_as` and `name` (true of some old, unregulated
    production data), reluctantly apply some cultural assumptions and build a
    name from parts (`given_name`, `additional_name`, `family_name`, `suffix`)

# [21.0.5] - 2021-03-12
- bugfix: in share.util.graph, handle merging nodes with dictionary values
- bugfix: when formatting oai_dc, strip characters illegal in XML
- when regulating, discard gravatars as agent identifiers

# [21.0.4] - 2021-03-11
- bugfix: deduping subjects in custom taxonomies

# [21.0.3] - 2021-03-10
- fix up `populate_osf_suids` with more useful messaging
- improve "central node" guessing to handle old osf data on prod

# [21.0.2] - 2021-03-09
- speed up `populate_osf_suids` -- exclude `NormalizedData` with null `raw`,
  since they'll be ignored anyway

# [21.0.1] - 2021-03-09
- fix `populate_osf_suids` script to handle fun situations

# [21.0.0] - 2021-03-09
- new model: `FormattedMetadataRecord`
- new sharectl commands:
    - `sharectl search purge`
    - `sharectl search setup <index_name>`
    - `sharectl search setup --initial`
    - `sharectl search set_primary <index_name>`
    - `sharectl search reindex_all_suids <index_name>`
- new management commands:
    - `format_metadata_records`
    - `populate_osf_suids`
- new doc: `README-docker-quickstart.md` -- the easy way to get started
- define the "share schema" statically (in `share.schema`)
    - stop inferring everything from the `ShareObject` models
- add a parallel ingestion path, preparing for a future without `ShareObject`
    - use only the most recent `NormalizedData` for each suid (no merging)
    - allow explicitly stating the suid when pushing a `NormalizedData`
        - if not specified, try looking for an OSF guid
    - build a `FormattedMetadataRecord` for each metadata format
    - currently two metadata formatters (and room for more):
        - `sharev2_elastic`: for a back-compatible elasticsearch index -- builds
          a document just like `share.search.fetchers.CreativeWorkFetcher`, but
          from a `NormalizedData` instead of all the `ShareObject` tables
        - `oai_dc`: dublin core XML, for the OAI-PMH feed
- indexer daemon overhaul
    - assorted cleanup; dead/useless code removal
    - add `ElasticManager` to encapsulate all requests sent to elasticsearch
    - add `IndexSetup` concept to describe how to get/build documents for an
      index and what messages to send to that index's daemon
    - currently two index setups:
        - `share_classic`: index by `AbstractCreativeWork` id, using existing
          `share.search.fetchers` logic
        - `postrend_backcompat`: index by `SourceUniqueIdentifier` id, using
          the `sharev2_elastic` `FormattedMetadataRecord`s
- add a parallel OAI-PMH that uses `FormattedMetadataRecord` with `oai_dc`
    - remains dormant for the moment -- enable with `pls_trove` query param
    - NOTE: when we switch over, OAI-PMH datestamps will all be new and recent
- admin updates:
    - search `IngestJob` by suid value

# [20.2.0] - 2020-09-03
- Add a decorator for marking views deprecated
- Mark some views deprecated
- Sources added via API default to canonical

# [20.1.0] - 2020-06-16
- Automatically schedule `ingest` tasks after harvesting
- Schedule `ingest` tasks in admin `reenqueue` action
- Pin `faker` to 4.0.3
- Update `.travis.yml`
- Fix bug in `io.osf.registrations` transformer

# [20.0.4] - 2020-01-13
- Ensure order in oai-pmh

# [20.0.3] - 2020-01-09
- Exclude frankenworks from oai-pmh

# [20.0.2] - 2020-01-06
- Reduce oai-pmh page size

# [20.0.1] - 2020-01-03
- Pin `graphql-relay` to a compatible version

# [20.0.0] - 2020-01-03
- Dockerfile fixes & improvements
- Optimize oai-pmh endpoint to avoid timeouts
- Add `reindex_works` shell util

# [19.0.6] - 2019-12-06
- Pin python-dateutil to a version that doesn't break tests (2.8.0)
- Temporarily (i hope) skip tests broken by 19.0.5

# [19.0.5] - 2019-12-06
- Temporary fix to avoid slow IngestJob queries

# [19.0.4] - 2019-02-25
- Possibly fix a rare forceingest error

# [19.0.3] - 2019-01-04
- Skip indexing works with too many agent relations

# [19.0.2] - 2019-01-03
- Make the indexer more configurable by environment variables

# [19.0.1] - 2019-01-02
- Fix indexer deadlock

# [19.0.0] - 2019-01-02
- Allow turning off ingestion (but not harvest) for non-canonical sources
- Ingestion perf improvements (faster attr access in MutableGraph)
- Handle indexer errors better

# [18.0.6] - 2018-12-13
- Ingestion perf improvements

# [18.0.5] - 2018-10-30
- Update `requests` dependency

# [18.0.4] - 2018-10-25
- Make it easier to reingest all OSF data

# [18.0.3] - 2018-10-24
- Fix worker out of memory errors

# [18.0.2] - 2018-10-23
- Update nameparser dependency

# [18.0.1] - 2018-10-23
- Add datacite oai-1.1 schema namespace
- Fix common datacite transform errors

# [18.0.0] - 2018-10-23
- Update django to 1.11.16
- Clean up disambiguation logic to make extending it less painful
- Extend disambiguation to match contributors with different name formats
- Rename `fixpreprintdisambiguations` command to `forceingest`
    - Handle more complex merges

# [2.16.11] - 2018-08-16
* Improve error message for transformer errors
* Fix OSF registration transformer

# [2.16.10] - 2018-07-30
* Update NSF harvester to look farther into the past
* Fix a bug in the OSF project harvester
* Fix --osf-only flag in fix_datacite command

# [2.16.9] - 2018-06-21
* When a job is marked "skipped", not even `superfluous` will re-run it

# [2.16.8] - 2018-06-14
* All retried jobs should be marked "rescheduled"

# [2.16.7] - 2018-06-14
* Harvest jobs that are retried when the same source is already being
  harvested should be marked "rescheduled" rather than "failed"

# [2.16.6] - 2018-06-14
* Handle OSF harvest errors gracefully

# [2.16.5] - 2018-06-04
* Pin kombu to 4.1.0

# [2.16.4] - 2018-06-04
* Harvest all set specs from CSIC
* Allow sorting Atom feed by `date_created` and `date_published`
* Don't create unnecessary source configs for each new source
* Update pytest-django dependency to avoid version conflict

# [2.16.3] - 2018-06-04
* Fix bug in indexer daemon, stop all threads when one dies

# [2.16.2] - 2018-04-30
* Fix typo in `sharectl ingest` that prevented bulk reingestion

# [2.16.1] - 2018-04-30
* Fix date range filtering in com.figshare.v2 harvester

# [2.16.0] - 2018-04-26
* Bulk reingestion with `IngestScheduler.bulk_reingest()` and `sharectl ingest`
* Admin interface updates
* More stable and reliable indexer daemon
* "Urgent" queues for ingestion and indexing, allowing pushed data to jump
  ahead of harvested data
* Various source config updates

# [2.15.6] - 2018-04-04
* Fix PeerJ transformer error

# [2.15.5] - 2018-03-15
* Prevent infinite task loop for certain types of errors

# [2.15.4] - 2018-03-15
* Update raw data janitor to skip over datums from disabled/deleted sources

# [2.15.3] - 2018-03-15
* Fix bug in fixpreprintdisambiguations command

# [2.15.2] - 2018-03-12
* Fix a broken test

# [2.15.1] - 2018-03-12
* Fix some time-sensitive tests

# [2.15.0] - 2018-03-05
## Ingest architecture
* Add IngestJob, used to keep track of a RawDatum's ingestion status
    * Exposed in API at `/api/v2/ingestjobs/`
    * In the response to pushed data, include a link to the IngestJob
* Rename HarvestLog to HarvestJob
* Combine `transform` and `disambiguate` tasks into `ingest` task
* Catch all errors caused by bad input data, store them on the IngestJob
* Add Regulator, a place to put logic/transforms/validation that should
  run on all data, regardless of source
* Fix: Prevent indexer daemon threads from exiting when elasticsearch times out

## Existing sources
* Map work relation types in MODS transformer
* Update edu.utah source config to include more approved sets
* Update edu.umassmed source config to use HTTPS

# [2.14.11] - 2018-02-26
* Update pendulum dependency to avoid infinite janitor loop

# [2.14.10] - 2018-02-26
* Fix elasticsearch_janitor task
    * Expect (and give) str arguments, avoiding error
    * Use the indexer daemon by default

# [2.14.9] - 2018-02-22
* Speed up update_elasticsearch task:
    * Don't count the works just for a log message
    * Use the indexer daemon by default, instead of index_model tasks
* Only run one update_elasticsearch task at a time

# [2.14.8] - 2018-02-22
* Add --delete-related and --superfluous flags to `enforce_set_lists`
* Improve script output by including ids in ShareObject.__repr__

# [2.14.7] - 2018-02-18
* Devops updates for new environment

# [2.14.6] - 2018-02-12
* *Actually* speed up OAI feed

# [2.14.5] - 2018-02-12
* Speed up OAI feed when filtering by `set`
* Delete merged works with no identifiers in `fixpreprintdisambiguations`

# [2.14.4] - 2018-02-08
* Allow omitting arXiv from `fix_datacite` script

# [2.14.3] - 2018-02-05
* Add parameters to `fix_datacite` script

# [2.14.2] - 2018-02-01
## Changed
* Use normalized agent name in Atom feed, instead of `cited_as`
* Update psycopg dependency

# [2.14.1] - 2018-01-18
## Added
* Type map for Columbia Academic Commons (edu.columbia)
* Type map for University of Cambridge (uk.cambridge)

# [2.14.0] - 2018-01-10
## Added
* Allow reading/writing `Source.canonical` at `/api/v2/sources/`
* Include `<author>` in atom feed at `/api/v2/atom/`
* ScholarsArchive@OSU source config for their new API

## Changed
* Prevent OSF harvester from being throttled
* Update NSFAwards harvester/transformer to include more fields

# [2.13.1] - 2018-01-04
## Fixed
* Use request context to build URLs in the API instead of SHARE_API_URL setting
    * Stop displaying `localhost:8000` links

## Added
* Add `--from` parameter to `fixpreprintdisambiguations` management command

# [2.13.0] - 2017-12-18
## Added
* Support for set blacklists for sources that follow OAI-PMH protocol
    * `enforce_set_lists` command to enforce set blacklist and whitelist
* Set whitelist for UA Campus Repository
* Support for encrypted json field and start using it in SourceConfig model
* Enable Coveralls
* Include work lineage (based on IsPartOf relations) in the search index payload
* Add `self` links to objects returned by the API

## Changed
* Collect metadata in MODS format from UA Campus Repository
* Update columbia.edu harvester source config (disabled set to false)
* Improve creating Sources at `/api/v2/sources/`
    * Use POST to create, PATCH to update
    * Respond with sensical status codes (409 on name conflict, etc.)

## Fixed
* Backfill CHANGELOG.md to include `2.10.0` and `2.11.0`
* Correctly encode &, <, > characters in the Atom feed
* Avoid DB connection leak by disabling persistent connections

# [2.12.0] - 2017-09-14
## Added
* `editsubjects` management command to modify `share/subjects.yaml`

## Changed
* Replace `share/models/subjects.json` with `share/subjects.yaml`
* Update central subjects taxonomy to match Bepress' 2017-07 update

# [2.11.0] - 2017-08-27
## Added
* Symbiota as a source
* AEA as a source

## Changed
* Used django-include for a faster OAI-PMH endpoint
* Updated regex for compatibility with Python 3.6

# [2.10.0] - 2017-08-03
## Added
* University of Arizona as a source
* NAU Open Knowledge as a source
* Started collecting analytics on source APIs (response time, etc.)
* Support for custom taxonomies

# [2.9.0] - 2017-06-15
## Added
* sharectl command line tool
* Profiling middleware for local development
* Janitor tasks to find and process unprocessed data
* Timestamp field to RawData
* Mendeley Harvester!
* Started to use deprecation warning
* Timeouts for harvests

## Removed
* The concept of "Bots"
* A lot of dead code
* A GPL licenced library

## Changed
* Upgraded to Celery 4.0
* Deleted works now return 403s from the API
* Deleted works are now excluded from the API
* Corrected to date fields used to audit the Elasticsearch index
* Strongly defined the Harvester interface
* Harvests are now scheduled in a more friendly manner
* Updated the configurations for many OAI sources

# Fixed
* HarvestLogs no longer get stuck in progress
* Text parsing transformer utilties
* MODS transformer looks at the location field in addition to other fields for a work identifier

# [2.8.0] - 2017-05-12
## Added
* Elasticsearch Janitor task to keep Postgres and ES in sync
* Concurrently added indexes
* Admin updates to allow quicker fixing of broken data
* More test coverage

## Removed
* Elasticsearch's scroll API explicitly disabled

## Changed
* Upgraded to Django 1.11
* Elasticsearch now pulls last_modified from itself rather than Postgres

## Fixed
* API pagination no longer times out on large collections
* Timestamps are now included in the ATOM feed

# [2.7.0] - 2017-05-04
## Added
* OAI endpoint
* Sources
  * OpenBU

## Changed
* Updated documentation

# [2.6.0] - 2017-03-28
## Added
* Sources
  * A table for managing SHARE data sources
  * Replaces the apps in the providers folder
* SourceConfigs
  * A table for managing different methods of acquire data from given source
  * Replaces nested apps/app labels
* HarvestLogs
  * First class support for managing harvesting/back harvesting
* Source Unique Identifiers
  * First class representation of what was RawData.provider_doc_id
* The Django admin now supports starting harvesters over long periods of time
* Support for the MODs OAI PHM prefix

## Removed
* Provider Django applications have been removed
* Source specific fields have been removed from ShareUser

## Changed
* Harvesters have been relocated to share/harvesters/
* Various renaming/vocabulary changes
  * RawData -> RawDatum
  * Favicon -> Icon
  * Provider -> Source
  * Provider App -> SourceConfig
  * Normalizer -> Transformer
* Updates to the getting started guide
* Squashed migrations to speed up local development
* Harvesters are now expected to return utf-8 strings
* Sources are no longer tied to the ShareUser model

## [2.5.0] - 2017-03-15
## Added
* Title now has an "exact" multi-field in elasticsearch
* A robot that archives old succeeded celery jobs
* New Harvesters
  * Scholarly Commons @ JMU

## Fixed
* Compensate for potential race conditions with the push API

## [2.4.0] - 2017-02-10
## Added
* New Harvesters
  * Research Registry Harvester
  * SSOAR
* Status API endpoint

## Changed
* Updated set_specs for University of Kansas
* ClinicalTrials.gov now output registrations
* Source icons are now stored in the database

## Fixed
* Removed "Notify" from the page title in the browsable API

## [2.3.0] - 2017-02-02
## Added
* Support for OSF Registries
* New Harvesters
  * University of Utah

## Changed
* Updated the API
* Improved Elasticsearch mappings
* Updated NIH and NSFAwards
  * Affiliations are now gathered
  * Non-Unique URLs are no longer collected
* Lots of under the hood changes to make dev's lives easier

## [2.1.0] - 2016-12-16
## Added
* New Harvesters
  * es.csic
  * edu.purdue.epubs
* Site status banners
* Retraction harvesting
* A little bit of documentation

## Changed
* OAuth login failure pages look nice now
* Cascade deletes are now implemented as database cascades

## [2.0.0] - 2016-12-02
### Added
* New Harvesters
  * edu.cornell
  * edu.richmond
  * edu.scholarworks_montana
  * edu.ucf
  * edu.umd
  * edu.utahstate
  * org.seafdec
* Relations between creative works
* Updated harvesters
  * Figshare v2 API
  * PeerJ XML API
  * Pubmed PMC prefix
  * Datacite 4.0
* BePress Taxonomy for subjects
* Travis now uses postgres 9.5
* Comprehensive test suite for normalization and disambiguation

### Changed
* Updated data model
  * More expressive relations between people/organizations and works
  * Type hierarchies
    * Creative works: Publication, Preprint, DataSet, Patent, Thesis, Software, etc.
    * Agents: Person, Organization, Institution, Consortium
* More aggressive and intelligent data parsing
* Stricter validation of incoming data
* Prune duplicate objects from submitted changesets
* Various bug fixes
* Formalized disambiguation methods
* App bootstrap time improved by 4x
* Better elasticsearch mappings
  * URI may now be searched/matched directly
* Prettier table names

## [1.0.0] - 2016-10-06
### Added
* Backport of the V1 push API
* New and improved source registration form
* JSON schema endpoint
* New sources
  * College of William and Mary
  * University of Wisconsin
