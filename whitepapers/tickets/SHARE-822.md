# [SHARE-822] Custom Taxonomies


## Goals:
   - Support OSF's Custom Taxonomies requirements
   - Have a solution that can be used by any parties interested in enhancing SHARE
   - Migrate the existing Subjecting system to this new solution
   - Continue to use the Bepress taxonomy as SHARE's central taxonomy


## Changes to SHARE:
  - New Model: "Taxonomy"
  - Changes to Model: "Subject"
    - Unique indexes on Subjects will move from `[name]` to `[name, taxonomy_id]` if the OSF requirements are ammenable to this
      Otherwise it will become `[name, taxonomy_id, parent_id]`
  - If we can upgrade to elasticsearch 5.4+ in time SHARE will index subjects using the new Path Hierarchy Tokenizer.
    Otherwise subjects will be manually indexed to act like the Path Hierarchy Tokenizer
  - Subjects will be indexed with the first element as the name of their Taxonomy to namespaces them appropriately
    IE: Bepress/A/B/C or Engrxiv/A/B/C
  - The Elasticsearch task will be updated to look for any related models that have been recently updated as well
  - A page will be added to the admin interface to support manually fixing Taxonomies if required

### Taxonomy

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

## Subject

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

## Changes to OSF: 
  - Whenever a custom taxonomy if modified the ne
  - The on_preprint updated method will now serialize subjects as:

## Situations:

### Reference
Taxonomy X:
  Subject Alpha -> Bepress A
    Subject Bravo -> Bepress B
      Subject Charlie -> Bepress C
    Subject Delta -> Bepress B
  Subject Echo -> Bepress D

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

  Rammifications:
    If "Gamma" is being submitted with "Bepress C" because "Charlie" impies it, "Bepress C" will
    have to be explicitly removed if "Charlie" is redefined.
    Works should only be submitted with subjects explicitly assigned by the user.

Given SHARE is aware of custom Taxonomy X and "Gamma" exists with subjects [Charlie, Delta]
When SHARE is notified that "Delta" has been deleted
Then SHARE will mark Delta as deleted and reindex all works attached to "Delta"

  Reasoning:
    "Delta" will have to exist for SHARE to detect the need to remove the subject from existing
    works.

### Strange Situations:
  - Custom Taxonomy item added
    - Foxtrot is added to Taxonomy X
  - Custom Taxonomy item removed
    - Bravo is added to Taxonomy X
    - Echo is added to Taxonomy X
  - Custom Taxonomy item renamed
    - Echo -> Romeo is added to Taxonomy X
  - Custom Taxonomy item redefined
    - Alpha -> Bepress B is added to Taxonomy X
  - Custom Taxonomy item duplicated
    - Foxtrot -> Bepress A is added to Taxonomy X
  - Preprint with Custom Taxonomy moves providers
