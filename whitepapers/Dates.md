# Partially Unknown Dates

## Overview
Many works in SHARE have the wrong publication date displayed, because many sources provide only partial publication dates for some works, such as "May 2017" or just "2017".
When the day of the month is omitted, the current date parsing logic assumes the first day of the month. When the month is omitted, it assumes January.

### Goals
Allow storing and displaying works with partially-known publication dates.

## Changes

Create a custom `PartialDate` class with:
* Three main properties:
    * `year`: integer (required)
    * `month`: integer (optional)
    * `day`: integer (optional)
* Missing/null values indicate an unknown date part
* Validation that set values are the correct type and correspond to a valid date
    * If `month` is missing, `day` must also be missing
* A way to construct a `PartialDate` from a `Date`-like object, string, or 8-digit integer (see below)

### Models
* Custom Django field `PartialDateField` that inherits from `IntegerField`
    * Store a `PartialDate` instance as an 8-digit integer in the database, `YYYYMMDD`
    * If `month` or `day` is null, put `00` in the `MM` or `DD` segment, respectively
        * "February 26, 2017" stored as `20170226`
        * "February 2017" stored as `20170200`
        * "2017" stored as `20170000`
    * This allows sorting and filtering by a `PartialDateField` in the database
        * Values with unknown month and day are sorted at the beginning of the year
        * Values with known month but unknown day are sorted at the beginning of the month
* Make `AbstractCreativeWork.date_published` a nullable `PartialDateField`

### Migrations
* Migrate columns on `share_creativework` and `share_creativeworkversion`
    * Create a new nullable `INTEGER` column `date_published_partial`
    * Find all special case dates, convert (see below), and copy them over appropriately
    * Convert all remaining values
    * Tell Django that `date_published`'s column is `date_published_partial`
    * Add a new field `_date_published` pointing at the column `date_published`
        * So we can keep it around for a little while
        * Drop the original `date_published` column in the next release
* Convert datetime values into integers, as above, dropping the "time" part of the datetime
    * If a value is at exactly midnight on the first day of the month, assume unknown day
        * If the month is January, also assume unknown month
    * Examples:
        * `2017-03-20 06:02:11` becomes `20170320`
        * `2017-03-20 00:00:00` becomes `20170320`
        * `2017-03-01 06:02:11` becomes `20170301`
        * `2017-03-01 00:00:00` becomes `20170300`
        * `2017-01-01 06:02:11` becomes `20170101`
        * `2017-01-01 00:00:00` becomes `20170000`

### Transformers
* Add a `PartialDateParser` Transformer link that parses a string into a `PartialDate` instance
    * Should also handle dates split into an array (e.g. `[2017, 3]`)
* Use `PartialDateParser` instead of `DateParser` for `CreativeWork.date_published` field in all Transformers

### JSON APIs
* Serialize `PartialDateField`s in JSON as an array of date parts:
    * `20171104` serialized as `[2017, 11, 4]`
    * `20171100` serialized as `[2017, 11]`
    * `20170000` serialized as `[2017]`

### Search Index
* Change `date_published` mapping to accept multiple date formats
    * `'format': 'yyyy-MM-dd||yyyy-MM||yyyy'`
* Update elasticsearch bot to format `date_published` accordingly
    * `20170101` indexed as "2017-01-01"
    * `20170100` indexed as "2017-01"
    * `20170000` indexed as "2017"
* Add `date_published.year`, `date_published.month`, `date_published.day` multi-fields
    * Use a pattern tokenizer to pull the correct part out of the date string
    * Queryable fields, but won't be included in search result body

### UI
* Anywhere `date_published` is displayed (search results and detail page), format it to omit unknown parts
    * `[2017, 07, 23]` displayed as "Jul 23, 2017" or "2017-07-23"
    * `[2017, 07]` displayed as "Jul 2017" or "2017-07"
    * `[2017]` displayed as "2017"
