Saint Cloud State University
====

The content of the SCSU repository is primarily faculty and student research, though there are some collections that are of a campus records nature. Since the material types are varied, we will have to only harvest from specific sets of records, rather than capture the whole repository. SCSU will provide a list of "series names" from which we should harvest.

Contact
----

Keith Ewing at St. Cloud State University, regarding content

Robert Allen at bepress, regarding issues with the OAI feed itself

Technical Resources
----

This will be an OAI-PMH harvest. This is a bepress institution and all the OAI feeds are provided by bepress. ([Wayne State](WayneState.md) is another bepress example.)

The OAI-PMH interface is here:
 
    http://repository.stcloudstate.edu/do/oai/

To see all the sets available use:

    http://repository.stcloudstate.edu/do/oai/?verb=ListSets&metadataPrefix=dcq

To retrieve a specific set use:

    http://repository.stcloudstate.edu/do/oai/?verb=ListRecords&metadataPrefix=dcq&set=publication:qebcr_sw_mn

The template for requests would be:

    http://repository.stcloudstate.edu/do/oai/?verb=[OAI-PHMVerb]&metadataPrefix=[oai_dc|qualified-dublin-core]&set=publication:[series_name]
     
_Provide any distinguishing characteristics of research outputs in your repository or sets that represent research outputs (as distinct from cultural heritage materials)._

Keith will provide a list of sets to retrieve during the week of 9/22/14, Eric will follow up to get it. This will be a list very similar to the [Wayne State](WayneState.md) list.

They have stretched the definition of the "article" document type, so that is not a good guide. ETDs are included in SCSU collections.
 
Metadata Sharing Questions
----

Responses provided by Keith Ewing on 9/17/2014.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your Terms of Service?_

No.

_Does metadata gathering violate your Privacy Policy?_

No.

_Does our sharing your metadata violate your Privacy Policy?_

No.

_What is the license of the metadata (e.g., CC Zero)?_

None yet.

_If unlicensed, will you explicitly license the content?_

We would consider it. We have not taken it that far, have not discussed it, but I [Keith] would vigorously argue for CC Zero. I now tell faculty that the abstracts and keywords are public and will be shared.