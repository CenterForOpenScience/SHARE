The Digital Archaeological Record
====

[The Digital Archaeological Record (tDAR)](http://core.tdar.org) is an international digital repository for the digital records of archaeological investigations. tDAR’s use, development, and maintenance are governed by [Digital Antiquity](http://www.digitalantiquity.org), an organization dedicated to ensuring the long-term preservation of irreplaceable archaeological data and to broadening the access to these data.

Contact
----

Primary Contact: Francis McManamon, Executive Director

Technology Contact: Adam Brin, Director of Technology

Technical Resources
----

This will be an OAI-PMH harvest using the system developed in-house for tDAR. More documentation about their API's can be found at [https://dev.tdar.org/confluence/display/DEV/Exposed+tDAR+APIs](https://dev.tdar.org/confluence/display/DEV/Exposed+tDAR+APIs).

The OAI-PMH interface is here:
 
    http://core.tdar.org/oai-pmh/oai

To see all the sets available use:

    http://core.tdar.org/oai-pmh/oai?verb=ListSets

The retrieval of specific sets is not supported, as seen at:

    http://core.tdar.org/oai-pmh/oai?verb=ListRecords&metadataPrefix=dcq&set=21222

The template for requests would be:

    http://core.tdar.org/oai-pmh/oai?verb=[OAI-PHMVerb]&metadataPrefix=[oai_dc|qualified-dublin-core]
 
_Provide any distinguishing characteristics of research outputs in your repository (as distinct from cultural heritage materials). Often this is a list of OAI-PMH "sets" or "series" encompassing research output that we should harvest from your repository._

All records at this repository represent research objects and so everything can be harvested.

Metadata Sharing Questions
----

Responses provided by Francis McManamon on 1/28/2015.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your terms of service?_

Metadata gathering does not violate our terms of service, [use of that metadata is unrestricted](https://www.tdar.org/about/policies/contributors-agreement/), though we would prefer that metadata is associated with a proper citation and attribution.

_Does metadata gathering violate your privacy policy?_

Metadata gathering does not violate our privacy policy.

_Does our sharing the metadata we gather from you violate your policies?_

No, it does not violate our policies. We would prefer that (a) any metadata pages are hidden behind a robots.txt such that they don't compete with our own metadata pages in search engine results, (b) are include proper citation and (c) link back to our canonical record.

_What is the license of the metadata (for example, CC Zero)?_

Our metadata does not have an explicit license. 

_If unlicensed, will you explicitly license the content?_

We have considered a CC0 license, but have not adopted it.