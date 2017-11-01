# Change Log

# Unreleased
## Added
* Support for set blacklists for sources that follow OAI-PMH protocol
* Set whitelist for UA Campus Repository

## Changed
* Collect metadata in MODS format from UA Campus Repository

## Fixed
* Backfill CHANGELOG.md to include `2.10.0` and `2.11.0`

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

## Fixed
* MODS transformer looks at the location field in addition to other fields for a work identifier

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
