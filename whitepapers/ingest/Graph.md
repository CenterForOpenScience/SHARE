# Graph Interface [NOT IMPLEMENTED]

Each stage of the [Ingest Pipeline](./README.md) creates, modifies, or uses a Graph object to represent the document being ingested from a particular source.

## Requirements

* Graph
  * Add a Node
  * Remove a Node
  * Iterate over:
    * All Nodes
    * Nodes of a given model
    * Nodes with a matching field/value pair
    * Nodes that match a given filter
  * Serialize/deserialize graph to/from a string
* Node
  * Get ID (immutable, unique within the Graph)
  * Get/set/modify model
  * Get/set/modify field values, given field name
  * Iterate over (field, value) pairs
  * Duplicate with overrides
    * Create copy of this node in the same graph
    * Required overrides, field-value pairs that will differ in the copy
    * Optionally cascade, duplicating nodes with edges pointing to this node
  * Delete
    * Remove this node from the graph
    * Optionally cascade, deleting nodes with edges pointing to this node
