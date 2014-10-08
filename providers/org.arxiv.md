arXiv
====

In addition to being a premier disciplinary repository, we are working with arXiv to learn how to harvest via ResourceSync.

Contact
----

Simeon Warner

Technical Resources
----

This will be a ResourceSync harvest.

Note that while ResourceSync does include a push protocol (code related to that may be what you saw Herbert announce recently), the arXiv implementation is of the pull protocol more analogous to OAI-PMH. I do believe we may want to consider implementing the push version to distribute data from the SHARE notification service, but with regard to arXiv we are looking at a harvest via ResourceSync. Simeon has some test server with a pointer to beta documentation available at http://resync.library.cornell.edu. Code for his simulator is available at https://github.com/resync/simulator.

There are no arXiv docs on ResourceSync support yet, Simeon is still working on getting this going (as of 7/22/2014). Current data is available from http://resync.library.cornell.edu with the Capability List for arXIv data at http://resync.library.cornell.edu/arxiv-all/capabilitylist.xml. This includes the full Resource List and a daily Change List. At present only the internal metadata format is available (e.g. http://resync.library.cornell.edu/arxiv/ftp/arxiv/papers/0711/0711.0198.abs) but he can perhaps make the same formats as are available via OAI-PMH available (see: http://arxiv.org/help/oa). It would be good to discuss what is most useful though.

Simeon notes that the arXiv API (http://arxiv.org/help/api) is not intended to full harvesting so that should not be considered.

Metadata Sharing Questions
----

Responses provided by Simeon Warner on 7/8/2014.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your Terms of Service?_

No. In fact, arXiv provides explicit permission to harvest via OAI, see http://export.arxiv.org/oai2?verb=Identify which states that "Metadata harvesting permitted through OAI interface." Even though this is explicit about OAI, Simeon assures me this will also apply to ResourceSync.

_Does metadata gathering violate your Privacy Policy?_

No.

_Does our sharing your metadata violate your Privacy Policy?_

No. Re-sharing is OK. While arXiv does not believe it has the right to give allow redistribution of the full text, it does allow redistribution of the metadata, including the abstracts. Full text can be harvested from arXiv and even ResourceSync will allow this, but that full text cannot be re-shared. For the purposes of the SHARE notification service, which is only sharing metadata, we should be in good shape.

_What is the license of the metadata (e.g., CC Zero)? Does that license extend to those beyond the group that gathered it? If unlicensed, will you explicitly license the content?_

There is currently no explicit license for the arXiv metadata and we should not expect anything like this soon, since introducing an explicit license would be a significant undertaking.
