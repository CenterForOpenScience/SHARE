Scholars Portal Dataverse Network
====

The [Scholars Portal Dataverse network](http://dataverse.scholarsportal.info/dvn/) is a repository for research data collected by individuals and organizations associated with Ontario universities. It is a service of the Ontario Council of University Libraries. It inlcudes an OAI-PMH service which we will use to harvest research release events from the network.

Contact
----

Steve Marks, works on preservation and technical aspects of the Scholars Portal, which hosts this Dataverse instance. Note that Steve will be on parental leave from October through December 2014.

Technical Resources
----

Note that "Dataverse" is used with a variety of scopes: the top level of dataverse installation is a dataverse "network" with a bunch of dataverse "instances" that appear as OAI sets. But the "Dataverse Network" can also refer to the whole [Dataverse project](http://thedata.org) run from Harvard.

Dataverse provides an OAI-PMH endpoint through which we can harvest research release events from the Scholars Portal. 

    http://dataverse.scholarsportal.info/dvn/OAIHandler

_Provide any distinguishing characteristics of research outputs in your repository (as distinct from cultural heritage materials). Often this is a list of OAI-PMH "sets" or "series" encompassing research output that we should harvest from your repository._

Consider everything in the repository research related. Scholars Portal is generally a place for space for data associated with an article. Sometimes it is a space for data in progress for teams that don’t want to use, for example, Dropbox. Some stuff may creep in that is not research generated data. From time to time there is government generated data. Some use dataverse as a repository for older data getting rebased every year. These are "corner cases."

_Do you include reports of updates to records via your API (if this is an OAI-PMH feed, are updates included)?_

Dataverse does allow versioning and fallback. Largely once things go in they don’t change that much. Allows for a pretty granular level of access, including to specific user accounts. You can close the metadata as well, or have open metadata with closed data. Closed metadata will take you to a landing page.

Metadata Sharing Questions
----

Responses provided by Steve Marks on 9/30/2014.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your terms of service?_

No. As long as the metadata is being exposed to harvest then that is right along with the terms of service. It is also crawled by Google.

_Does metadata gathering violate your privacy policy?_

No.

_Does our sharing the metadata we gather from you violate your policies?_

No.

_What is the license of the metadata (for example, CC Zero)?_

The metadata is out there, but not covered explicit license.

_If unlicensed, will you explicitly license the metadata?_

We've talked about it, but not gone that way yet. The more we've tried to mandate things the more they run the other way. Researchers may be spooked by a requirement for CC0 on their metadata.
