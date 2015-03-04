ASU Digital Repository
====

[ASU Digital Repository](http://repository.asu.edu) provides a central place to collect, preserve, and discover the creative and scholarly output from ASU faculty, research partners, staff and students. It provides free, online access to ASU scholarship benefits our local community, encourages transdisciplinary research, and engages scholars and researchers worldwide, increasing impact globally through the rapid dissemination of knowledge.

Contact
----

Mary Whelan, Geospatial and Research Data Manager

Technical Resources
----

This will be an OAI-PMH harvest using the system developed in-house for tDAR. More documentation about their API's can be found at [https://dev.tdar.org/confluence/display/DEV/Exposed+tDAR+APIs](https://dev.tdar.org/confluence/display/DEV/Exposed+tDAR+APIs).

The OAI-PMH interface is here:
 
    http://repository.asu.edu/oai-pmh

To see all the sets available use:

    http://repository.asu.edu/oai-pmh?verb=ListSets

The retrieval of specific sets is not supported, as seen at:

    http://repository.asu.edu/oai-pmh?verb=ListRecords&metadataPrefix=oai_dc&set=research

The template for requests would be:

    http://repository.asu.edu/oai-pmh?verb=[OAI-PHMVerb]&metadataPrefix=[oai_dc|qualified-dublin-core]&set=publication:[series_name]
 
_Provide any distinguishing characteristics of research outputs in your repository (as distinct from cultural heritage materials). Often this is a list of OAI-PMH "sets" or "series" encompassing research output that we should harvest from your repository._

None to speak of, most collections are cultural heritage. Sets are configurable, a repository manager would need to maintain a set dedicated to research-oriented collections. Only records which are in the set "research" should be included in SHARE.

Updates are included, datestamp-based selective harvesting is supported. Deleted records are currently ```transient``` as defined by the OAI-PMH spec, but will soon be ```persistent``` with an impending update.

Metadata Sharing Questions
----

Responses provided by Francis McManamon on 1/28/2015.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your terms of service?_

No.

_Does metadata gathering violate your privacy policy?_

No.

_Does our sharing the metadata we gather from you violate your policies?_

No.

_What is the license of the metadata (for example, CC Zero)?_

CC0, see specifics at [http://repository.asu.edu/about/policies/metadata/](http://repository.asu.edu/about/policies/metadata/).

