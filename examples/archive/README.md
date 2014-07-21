This is an example of what the archive directory structure would look like.

````
Service
    |__Unique_ID
    |   |__Timestamp
    |   |   |__manifest.json (record of how document was generated)
    |   |   |__raw.* (The raw file, grabbed from API. Filetype varies by service)
    |   |   |__normalized.json (a normalized JSON representation of the raw file)
    |   |__Timestamp
    |       |__manifest.json
    |       |__raw.*
    |       |__normalized.json
    |__Unique_ID
        |__Timestamp
            |__manifest.json
            |__raw.*
            |__normalized.json
````
etc...
