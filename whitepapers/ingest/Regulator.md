# Regulator

## Responsibilities
* Run a series of cleaning steps on a graph, modifying it in place.
* Generate a human-readable reason for each modification.
* Validate the graph against a set of criteria.
* If the graph has problems the Regulator cannot fix, or if the graph fails validation, halt with an error.

## Parameters
* `ingest_job` (optional) -- [IngestJob](../Tables.md#IngestJob)
* `graph` -- [MutableGraph](./Graph.md) object, output from a [Transformer](./Transformer.md)

## Phases of Regulation
* Source-specific Phase
  * `suid.source_config` can contain a list of regulator steps that will run first
* Node Phase
  * Static list of regulator steps that run on each node individually
  * Each step makes decisions based only on the information in the given node
  * Possible effects:
    * Modify the given node
    * Delete the given node
    * Add new nodes to the graph
      * Added nodes will be run through a Node Phase separately
* Graph Phase
  * Static list of regulator steps that run on the entire graph
  * Decisions based on information across multiple nodes
  * Can modify any part of the graph in any way
    * Added nodes will be run through a Node Phase separately
* Validation Phase
  * Static list of regulator steps that run on the entire graph
  * Cannot modify the graph
  * Each phase tests the graph against a criterion
    * Halts with an error if the graph fails

## Example Regulator Steps
* Node-Phase Steps
  * tokenize
    * recognize when a single field has multiple values
      * tag.name has list of tags
      * agent.name has list of names
    * remove all but first value
    * create nodes for each additional value
        * if splitting an agent that is a creator on a work with order_cited=1, new creator nodes should have order_cited 1.1, 1.2, etc.
  * rich agent names
    * recognize when agent.name contains more information than just a name
      * email address
      * location
      * affiliated organization/institution
    * remove excess info from the name
    * create nodes for excess info
  * person name parts
    * if a person has a `name`, but not given/family names, parse `name` into parts
    * if a person has given/family names but no `name`, concat the parts and assign to `name`
  * cited as
    * if an agent-work relation has missing/empty `cited_as`, copy `name` from the agent
  * normalize white space
    * look at each text field
    * remove leading or trailing whitespace
    * replace repeated whitespace or newlines, tabs, etc. with a single space
* Graph-Phase Steps
  * order cited
    * look at `order_cited` for all creators for each work
    * sort by `order_cited` and ensure all values are integers
      * e.g. (0, 0.1, 0.2, 1.0, 1.1) -> (0, 1, 2, 3, 4)
    * if any creators have null `order_cited`, add them to the end in alphabetical order
      * or fail?
  * prune duplicate nodes
    * find identical pairs of nodes, or nodes with duplicate values in a unique field
    * delete one of the duplicate nodes
  * delete invalid nodes
    * delete works that have no identifiers
    * delete agents that meet all conditions:
      * have no identifiers
      * have no relations to a work
      * have no relations to an agent with an identifier(?)
    * delete all other nodes that are not somehow connected to an agent or work
* Validation-Phase Steps
  * required fields
    * all required fields for a node's model (and type) must be present
  * field values
    * scalar fields: field values must be appropriate type/format/value for the field
    * relation fields: related nodes must have the correct model for the field
  * required identifiers
    * works must have at least one identifier
    * agents must have either an identifier or a related work

## Error conditions
* Duplicate node IDs -> Fail ingestion
