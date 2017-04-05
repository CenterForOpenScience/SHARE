# Build Task (NOT IMPLEMENTED)


## Responsibilities
* Combining all states that refer to the same resource
* Selecting the most appropriate attributes from each state to use
* Translating from state foreign keys to final foreign keys


## Parameters
* `final_ids` -- A list of PK for to be built or rebuilt
* `content_type_id` -- The content type of the resource being built
* `superfluous` -- Rebuild even if nothing has changed


## Steps
* For each Final model
  * Load all states referencing this `final_id`
  * Elect the highest rated scalar value fromo all states
    * Scalar Score = (Source Weight + Field score + Age (Newer is better))
  * For every concrete related value load all the reference `final_ids` of the related states distinctly
    * If # found > 1 or < 1 Crash
  * Update Build Date and Build Version
  * Set Build Key to SHA256(Source Weight + State Id + State Last Modified For each State ordered by state Id)
