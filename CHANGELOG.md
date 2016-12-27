# Change Log

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
