# Change Log

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
