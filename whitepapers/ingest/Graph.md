# MutableGraph [NOT IMPLEMENTED]

Each stage of the [Ingest Pipeline](./README.md) creates, modifies, or uses a MutableGraph object to represent the document being ingested from a particular source.

Since the MutableGraph is only used for freshly ingested data, it assumes that node types and field/attribute names conform to the current version of the SHARE schema.

## Interface
* MutableGraph
  * Get Node by ID
  * Add Node
    * Given node ID, type, and attributes
  * Remove Node
    * Optionally cascade, deleting nodes with edges pointing to the removed node
  * Iterate over:
    * All Nodes
    * Nodes of a given model
    * Nodes that match a given field/value pair
    * Nodes for which a given filter returns True
  * Serialize graph to JSON-LD (or some other format)
  * Construct graph from JSON-LD (or some other format)
* MutableNode
  * Get/set type
  * Get model for the type
  * Get value for a field
    * For attributes (non-relation fields), acts like a simple key/value store
    * For outgoing edges (foreign key fields), value is the MutableNode the edge points to
    * For incoming edges (one-to-many fields), value is the set of MutableNodes the edges come from
  * Set/delete attributes and outgoing edges
  * Iterate over (field, value) pairs, for attributes and outgoing edges
