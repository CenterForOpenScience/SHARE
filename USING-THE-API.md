# Using the API

## Good things to use

`/oaipmh` -- an implementation of the Open Access Initiative's [Protocol for Metadata Harvesting](https://www.openarchives.org/OAI/openarchivesprotocol.html)


## Things that might shift out from under you

`/api/v2/search` -- an exposed elasticsearch instance which should (and will...)
be hidden behind a cleaner, public search API

`/api/v2/normalizeddata` -- how to push data into SHARE/Trove (currently used
only by other COS projects, not yet for public use)
