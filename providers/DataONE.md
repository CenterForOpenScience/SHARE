DataONE
====

Contact
----

Dave Vieglais

Technical Resources
----

DataONE has its own API at http://releases.dataone.org/online/api-documentation-v1.2.0/

There are two ways to approach this at DataONE, a list-objects API that would provide a more robust list of new resources, but without any normalized metadata, or a search against the SOLR index using date-created stamps approach, which would result in more easily parsable metadata but at the cost of some latency while new datasets are waiting to be indexed in SOLR. SHARE probably wants to go with the second approach since we don't really want to send notifications out until the records are indexed and available at DataONE coordinating nodes anyway.

Similarly, there are choices to be made about the URL we link back to when referencing the resources. DataONE has a resolve endpoint that takes a DataONE identifier and produces a redirect back to the original dataset. However, that would usually result in an immediate file download rather than a landing page for anyone following the link. They are working on, but have not yet deployed, a "view service" that will provide a web-friendly landing page for human consumption. In the meantime, it may be that a link could be created to hit their ONEMercury search engine with a request that would essentially generate a landing page of some sort.

Finally, this is a case where the nature of "source" comes into play. DataONE would be the "source" of this metadata from SHARE's perspective. But DataONE is, itself, an aggregator. The real source of the datasets are DataONE "member nodes" and we should credit them as such. This may also come into play with sources like bePress down the road.

Metadata Sharing Questions
----

Responses provided by Dave Vieglais on 20140731.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your Terms of Service?_

No, gathering metadata via the DataONE API does not violate terms of service.

_Does metadata gathering violate your Privacy Policy?_

No, DataONE is making a point of avoiding domains that require strict privacy managment.

_Does our sharing your metadata violate your Privacy Policy?_

I don’t think this violates any kind of policy. We would like you to try to provide referrals back to the origin of the data sets. Most important thing is that when a user goes to retrieve the content they are are redirected back to the holding repository. If presenting a list of recent content, then those links should point to the content at the source. Pointing users to our resolve endpoint or view service would be sufficient for these purposes.

_What is the license of the metadata (e.g., CC Zero)? Does that license extend to those beyond the group that gathered it? If unlicensed, will you explicitly license the content?_

Metadata license is per-institution and should be expressed in the metadata itself. The system metadata which describes what a thing is has no restrictions on it whatsoever.

