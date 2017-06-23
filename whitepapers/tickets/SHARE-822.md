# [SHARE-822] Custom Taxonomies


## Goals:
 - Support OSF's Custom Taxonomies requirements
 - Have a solution that can be used by any parties interested in enhancing SHARE
 - Migrate the existing Subjecting system to this new solution
 - Continue to use the Bepress taxonomy as SHARE's central taxonomy


## Reference
The following values will be refered to for examples throughout this document

```
Taxonomy X:
  Subject Alpha -> Bepress A
    Subject Bravo -> Bepress B
      Subject Charlie -> Bepress C
    Subject Delta -> Bepress B
  Subject Echo -> Bepress D
```



## Changes to OSF

Changes are to be done by the OSF team.

OSF's serialization of `Subject`s and `ThroughSubject`s in the `on_preprint` updated method will neeed to be modified.


### Subject

```javascript
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",

  "properties": {
    "@id": {"type": "string"},  // Unchanged
    "@type": {"enum": ["subject"] },  // Unchanged
    "name": {"type": "string"}, // Unchanged
    "parent": {"type": {"$ref": "#/definitions/reference"}},  // Unchanged

    "central_synonym": {
      "type": {"$ref": "#/definitions/reference"}
      "default": null,
      "description": "The central (Currently Bepress) subject that this subject is equivalent to."
      // Nullable right now. It might make sense to make this a self reference for Bepress Subject
      // Either way if a matching Name of Bepress is not found this entire graph will be rejected
    },
    "is_deleted": {
      "type": "boolean",
      "default": false,
      "description": "Indicates whether or not this subject will be surfaced in SHARE.",
    },
    "uri": {
      "type": "uri",
      "description": "A URI to this subject, does not have to resolve. Allows uses to specify the exact subject to change"
      // We could potentially use @id for the same purpose
    }
  },

  "additionalProperties": false,
  "required": ["@id", "@type", "name", "uri"]

  "definitions": {
    "reference": {
      "type": "object",
      "properties": {
          "@id": { "type": "string" },
          "@type": { "type": "string" }
      },
      "additionalProperties": false
      "required": [ "@id", "@type" ],
    }
  }
}
```

### ThroughSubjects

```javascript
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",

  "properties": {
    "@id": {"type": "string"},  // Unchanged
    "@type": {"enum": ["throughsubjects"] },  // Unchanged
    "subject": {"type": {"$ref": "#/definitions/reference"}}  // Unchanged
    "creative_work": {"type": {"$ref": "#/definitions/reference"}}  // Unchanged

    "is_deleted": {
      "type": "boolean",
      "default": false,
      "description": "Indicates whether or not this subject will be surfaced in SHARE.",
    },
    "uri": {
      "type": "uri",
      "description": "A URI to this throughsubject, does not have to resolve. Allows users to explicitly remove subjects. Note: If URI is omitted, there will be no programatic way to remove this ThroughSubject."
    }
  },

  "additionalProperties": false,
  "required": ["@id", "@type", "name"]

  "definitions": {
    "reference": {
      "type": "object",
      "properties": {
          "@id": { "type": "string" },
          "@type": { "type": "string" }
      },
      "additionalProperties": false
      "required": [ "@id", "@type" ],
    }
  }
}
```


## Changes to SHARE:

  - New Model: "Taxonomy"
  - Changes to Model: "Subject"
    - Unique indexes on Subjects will move from `[name]` to `[name, taxonomy_id]` if the OSF requirements are amenable to this
      Otherwise it will become `[name, taxonomy_id, parent_id]`
  - Subjects will be indexed using the Path Hierarchy Tokenizer.
  - Subjects will be indexed with the first element as the name of their Taxonomy to namespaces them appropriately
    IE: Bepress/A/B/C or Engrxiv/A/B/C
  - The Elasticsearch task will be updated to look for any related models that have been recently updated as well
  - A page will be added to the admin interface to support manually fixing Taxonomies if required

### New Models

#### Taxonomy

| Column        |   Type   | Indexed | Nullable | FK  | Default | Description                                    |
| :------------ | :------: | :-----: | :------: | :-: | :-----: | :--------------------------------------------- |
| name          |   text   | unique  |          |     |         | The human readable name for this taxonomy      |
| deleted       |   bool   |         |          |     |         | Whether or not this taxonomy is deleted/usable |
| date_created  | datetime |         |          |     |         |                                                |
| date_modified | datetime |  Desc   |          |     |         |                                                |

| id  | name          | deleted |
| --- | ------------- | ------- |
| 1   | Bepress       | False   |
| 1   | My custom tax | False   |

#### Subject

| Column        |   Type   | Indexed | Nullable | FK  | Default | Description                                                                                        |
| :------------ | :------: | :-----: | :------: | :-: | :-----: | :------------------------------------------------------------------------------------------------- |
| name          |   text   |         |          |     |         | The subject name                                                                                   |
| deleted       |   bool   |         |          |     |         |                                                                                                    |
| handle        |   text   | unique  |          |     |         | A unique refence to this subject that Sources may use to specify which subject needs to be altered |
| taxonomy_id   |   int    |    ✓    |          |  ✓  |         | The taxonomy this subject belongs to                                                               |
| alias_id      |   int    |    ✓    |          |  ✓  |         | The Bepress equivalent of this subject. Set to id if this subject belongs to Bepress.              |
| parent_id     |   int    |    ✓    |    ✓     |  ✓  |         |                                                                                                    |
| date_created  | datetime |         |          |     |         |                                                                                                    |
| date_modified | datetime |  Desc   |          |     |         |                                                                                                    |

| id  | name       | deleted | handle    | taxonomy_id | bepress_id | parent_id |
| --- | ---------- | ------- | --------- | ----------- | ---------- | --------- |
| 1   | Law        | False   | Law       | 1           | 1          | NULL      |
| 2   | Civil Law  | False   | Civil Law | 1           | 2          | 1         |
| 3   | Custom Law | False   | 538df3e1  | 2           | 1          | 1         |


### Changes to Admin
  - The Django admin should have a subjects page added to it to allow manual correction of errors

### Changes to Elasticsearch
  - The `subjects` fields of `CreativeWorks` will now use the Path Hierarch Tokenizer
  - Subjects should be deduplicated before being indexed into elasticsearch
    - A work with subject `Alpha` and `Charlie` will be indexed as `Taxonomy/Alpha/Bravo/Charlie`
  - Subjects and ThroughSubjects that have been marked as `is_deleted` should not be included in `subjects`
  - The `date_modified` of subjects will now be considered when looking for works that are out of date

### Changes to Changes
  - If a model does not have a `date_updated` field and the `NormalizedData` that it originates from does, that date will be used in place of `date_updated`
    when resolving conflicting changes.


## Situations

Given SHARE is aware of custom Taxonomy X
When SHARE recieves a work, "Gamma", with subjects [Alpha, Bravo, Charlie]
Then SHARE will remove all parent subjects as they will be implied by subject "Charlie"

  Reasoning:
    If at any point "Charlie" is moved to another location in Taxonomy X no changes need to
    be made to "Gamma", we simply find all works that haven't been modified since "Charlie"
    has been modified and re-index them.

Given SHARE is aware of custom Taxonomy X
When SHARE recieves a work, "Gamma", with subjects [Charlie, Bepress C, Bepress D]
Then SHARE will not modify the submitted subjects

  Reasoning:
    "Charlie" may currently imply that "Bepress C" is attached to "Gamma". If "Charlie" is
    ever redefined to be a different Bepress subject that implication will no longer be true.

  Ramifications:
    If "Gamma" is being submitted with "Bepress C" because "Charlie" implies it, "Bepress C" will
    have to be explicitly removed if "Charlie" is redefined.
    Works should only be submitted with subjects explicitly assigned by the user.

Given SHARE is aware of custom Taxonomy X and "Gamma" exists with subjects [Charlie, Delta]
When SHARE is notified that "Delta" has been deleted
Then SHARE will mark Delta as deleted and reindex all works attached to "Delta"

  Reasoning:
    "Delta" will have to exist for SHARE to detect the need to remove the subject from existing
    works.
 ```

### Strange Situations

- Custom Taxonomy item added
  - Foxtrot is added to Taxonomy X
- Custom Taxonomy item removed
  - Bravo is removed to Taxonomy X
  - Echo is removed to Taxonomy X
- Custom Taxonomy item renamed
  - Echo -> Romeo is added to Taxonomy X
- Custom Taxonomy item redefined
  - Alpha -> Bepress B is added to Taxonomy X
- Custom Taxonomy item duplicated
  - Foxtrot -> Bepress A is added to Taxonomy X
- Preprint with Custom Taxonomy moves providers
