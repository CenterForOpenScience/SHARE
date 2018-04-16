# TODO replace asserts with actual Errors

import networkx as nx

from django.apps import apps


# TODO get SHARE schema in a non-model form
def resolve_model(type):
    return apps.get_model('share', type)


class MutableGraph(nx.DiGraph):
    """NetworkX DiGraph with some SHARE-specific features.

    Nodes in the DiGraph are string IDs. Uses MutableNode as a convenience interface to access/manipulate nodes.

    Provides the abstraction of named edges:
        * Each named edge has two names: `from_name` and `to_name`
            * the "from" node knows the edge by its `from_name`
            * the "to" node knows the edge by its `to_name`
            * correspond to a foreign key and its related field
        * All outgoing edges from a node must be unique on `from_name`


    Example: Find all URIs identifying a work
        ```
        work = graph.get_node(work_id)
        uris = [identifier['uri'] for identifier in work['identifiers']]
        ```

    Example: Remove all orphan nodes (no incoming or outgoing edges)
        ```
        orphans = graph.filter_nodes(lambda n: not graph.degree(n))
        for orphan in orphans:
            graph.remove_node(orphan.id)
        ```
    """
    FROM_NAME_ATTR = '__from_name'
    TO_NAME_ATTR = '__to_name'

    @classmethod
    def from_jsonld(cls, nodes):
        """Create a mutable graph from a list of JSON-LD-style dicts.
        """
        if isinstance(nodes, dict):
            nodes = nodes['@graph']
        graph = cls()
        for n in nodes:
            id, type = None, None
            attrs = {}
            for k, v in n.items():
                if k == '@id':
                    id = v
                elif k == '@type':
                    type = v
                    type = v
                elif isinstance(v, dict) and k != 'extra':
                    graph.add_node(v['@id'], v['@type'])
                    attrs[k] = v['@id']
                elif isinstance(v, list):
                    pass  # Don't bother with incoming edges, let the other node point here
                else:
                    attrs[k] = v
            assert id and type
            graph.add_node(id, type, **attrs)
        return graph

    def to_jsonld(self, in_edges=True):
        """Return a list of JSON-LD-style dicts.

        in_edges (boolean): Include lists of incoming edges. Default True.
        """
        return [node.to_jsonld(in_edges=in_edges) for node in self]

    def add_node(self, id, type, **attr):
        """Create a node in the graph.

        id (hashable): Unique node ID
        type (str): Name of the node's model
        keyword args: Named attributes or relations corresponding to fields on the node's model

        Returns a MutableNode wrapper for the new node.
        """
        super().add_node(id)
        node = MutableNode(self, id)
        node.type = type
        node.update(attr)
        return node

    def get_node(self, id):
        """Get a node by ID.

        id (hashable): Unique node ID

        Returns a MutableNode wrapper for the node, or None.
        """
        if id in self:
            return MutableNode(self, id)
        return None

    def remove_node(self, id, cascade=True):
        """Remove a node and its incoming/outgoing edges.

        id (hashable): Unique node ID
        cascade (boolean): Also remove nodes with edges which point to this node. Default True.
        """
        to_remove = list(self.predecessors(id)) if cascade else []
        super().remove_node(id)
        for from_id in to_remove:
            self.remove_node(from_id, cascade)

    def filter_nodes(self, filter):
        """Filter the nodes in the graph.

        filter (callable): When called with a MutableNode argument, return something truthy to
            include it in the filtered list, or something falsy to omit it.

        Returns list of MutableNodes.
        """
        # TODO figure out common sorts of filters, make kwargs for them and optimize
        return [node for node in self if filter(node)]

    def filter_type(self, type_name):
        # TODO make a sort of index dict, mapping type to nodes
        return self.filter_nodes(lambda n: n.type == type_name)

    def add_named_edge(self, from_id, to_id, from_name, to_name):
        """Add a named edge.

        from_id (hashable): Unique ID for the node this edge comes from
        to_id (hashable): Unique ID for the node this edge points to
        from_name (str): Name of the edge on its 'from' node (must be unique on the node)
        to_name (str): Name of the edge on its 'to' node
        """
        assert all(
            data.get(self.FROM_NAME_ATTR) != from_name for _, _, data
            in self.out_edges(from_id, data=True)
        ), 'Out-edge names must be unique on the node'
        self.add_edge(from_id, to_id, **{self.FROM_NAME_ATTR: from_name, self.TO_NAME_ATTR: to_name})

    def remove_named_edge(self, from_id, from_name):
        """Remove a named edge.

        from_id (hashable): Unique ID for the node this edge comes from
        from_name (str): Name of the edge on its 'from' node
        """
        try:
            to_id = next(
                to_id for _, to_id, data
                in self.out_edges(from_id, data=True)
                if data.get(self.FROM_NAME_ATTR) == from_name
            )
            self.remove_edge(from_id, to_id)
        except StopIteration:
            pass

    def resolve_named_out_edge(self, from_id, from_name):
        """Get the node a named edge points to.

        from_id (hashable): Unique ID for the node this edge comes from
        from_name (str): Name of the edge on its 'from' node

        Returns a MutableNode wrapper for the node the edge points to.
        """
        try:
            return next(
                MutableNode(self, to_id) for _, to_id, data
                in self.out_edges(from_id, data=True)
                if data.get(self.FROM_NAME_ATTR) == from_name
            )
        except StopIteration:
            return None

    def resolve_named_in_edges(self, to_id, to_name):
        """Get all nodes which point to a node with the same named edges.

        to_id (hashable): Unique ID for the node these edges point to
        to_name (str): Name of the edges on their 'to' node

        Returns list of MutableNode wrappers for the nodes these edges come from.
        """
        return [
            MutableNode(self, from_id) for from_id, _, data
            in self.in_edges(to_id, data=True)
            if data.get(self.TO_NAME_ATTR) == to_name
        ]

    def named_out_edges(self, from_id):
        """Get all outgoing named edges from a node.

        from_id (hashable): Unique node ID

        Returns dict with:
            keys: `from_name` of each outgoing edge
            values: MutableNode wrapper for the node each edge points to
        """
        return {
            data[self.FROM_NAME_ATTR]: MutableNode(self, to_id) for _, to_id, data
            in self.out_edges(from_id, data=True)
            if data.get(self.FROM_NAME_ATTR) is not None
        }

    def named_in_edges(self, to_id):
        """Get all incoming named edges to a node.

        to_id (hashable): Unique node ID

        Returns dict of edges with:
            keys: `to_name` of each incoming edge
            values: list of MutableNode wrappers for the nodes each edge comes from
        """
        in_edges = {}
        for from_id, _, data in self.in_edges(to_id, data=True):
            to_name = data.get(self.TO_NAME_ATTR)
            if to_name is not None:
                in_edges.setdefault(to_name, []).append(MutableNode(self, from_id))
        return in_edges

    def __iter__(self):
        return (MutableNode(self, id) for id in super().__iter__())

    def __contains__(self, n):
        if isinstance(n, MutableNode):
            n = n.id
        return super().__contains__(n)

    def __bool__(self):
        return bool(len(self))


class MutableNode:
    """Convenience wrapper around a node in a MutableGraph.
    """

    def __init__(self, graph, id):
        self.__graph = graph
        self.__id = id

    @property
    def id(self):
        return self.__id

    @property
    def graph(self):
        return self.__graph

    @property
    def attrs(self):
        return self.graph.nodes[self.id]

    @property
    def type(self):
        # TODO something else
        return self.attrs['@type']

    @type.setter
    def type(self, value):
        self.attrs['@type'] = value

    @property
    def model(self):
        return resolve_model(self.type)

    def __getitem__(self, key):
        """Get an attribute value or related node(s).

        key (str): Name of an attribute, outgoing named edge, or incoming named edge.

        If key is the name of a plain attribute in the SHARE schema, return that attribute's value.
        If key is the name of an outgoing edge, return a MutableNode that edge points to
        If key is the name of incoming edges, return a list of MutableNodes those edges come from
        """
        # TODO exclude fields not in the SHARE schema
        field = self.model._meta.get_field(key)
        if field.is_relation and key != 'extra':
            assert field.many_to_one or field.one_to_many
            if field.many_to_one:
                return self.graph.resolve_named_out_edge(self.id, field.name)
            if field.one_to_many:
                return self.graph.resolve_named_in_edges(self.id, field.name)
        return self.attrs.get(key)

    def __setitem__(self, key, value):
        """Set an attribute value or add an outgoing named edge.

        key (str): Name of an attribute or an outgoing edge.

        If key is the name of a plain attribute in the SHARE schema, set that attribute's value.
        If key is the name of an outgoing edge, expect `value` to be a node ID or a MutableNode. Add an edge from this node to that one.
        If key is the name of incoming edges, raise an error.
        """
        # TODO exclude fields not in the SHARE schema
        field = self.model._meta.get_field(key)
        if field.is_relation and key != 'extra':
            assert field.many_to_one
            to_id = value.id if hasattr(value, 'id') else value
            self.graph.remove_named_edge(self.id, field.name)
            self.graph.add_named_edge(self.id, to_id, field.name, field.remote_field.name)
        else:
            self.attrs[key] = value

    def __delitem__(self, key):
        """Delete an attribute value or outgoing named edge.

        key (str): Name of an attribute or an outgoing edge.

        If key is the name of an attribute in the SHARE schema, delete that attribute from this node.
        If key is the name of an outgoing edge, remove that edge.
        If key is the name of incoming edges, raise an error.
        """
        field = self.model._meta.get_field(key)
        if field.is_relation and key != 'extra':
            assert field.many_to_one
            self.graph.remove_named_edge(self.id, field.name)
        else:
            del self.attrs[key]

    def update(self, dict):
        for k, v in dict.items():
            self[k] = v

    def delete(self, cascade=True):
        """Remove this node from its graph.

        cascade (boolean): Also remove nodes with edges which point to this node. Default True.
        """
        self.graph.remove_node(self.id, cascade)
        self.__graph = None

    def to_jsonld(self, ref=False, in_edges=True):
        ld_node = {
            '@id': self.id,
            '@type': self.type,
        }
        if not ref:
            ld_node.update(self.attrs)
            for from_name, node in self.graph.named_out_edges(self.id).items():
                ld_node[from_name] = node.to_jsonld(ref=True)
            if in_edges:
                for to_name, nodes in self.graph.named_in_edges(self.id).items():
                    ld_node[to_name] = [n.to_jsonld(ref=True) for n in sorted(nodes, key=lambda n: n.id)]
        return ld_node

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.graph is self.graph and other.id == self.id

    def __hash__(self):
        return hash(self.id)
