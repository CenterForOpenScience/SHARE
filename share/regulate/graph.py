# TODO replace asserts with actual Errors

import networkx as nx

from django.apps import apps


# TODO get SHARE schema in a non-model form
def resolve_model(type):
    return apps.get_model('share', type)


class MutableGraph(nx.DiGraph):
    """NetworkX DiGraph with some SHARE-specific features.

    Nodes in the DiGraph are string IDs. Uses MutableNode as a convenience interface to access/manipulate nodes.

    Provides the abstraction of named directed edges:
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

    @classmethod
    def from_jsonld(cls, nodes):
        """Create a mutable graph from a list of JSON-LD-style dicts."""
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
                elif isinstance(v, dict):
                    graph.add_node(v['@id'], v['@type'])
                    attrs[k] = v['@id']
                elif isinstance(v, list):
                    pass  # Don't bother with incoming edges, let the other node point here
                else:
                    attrs[k] = v
            assert id and type
            graph.add_node(id, type, **attrs)
        return graph

    def to_jsonld(self):
        """Return a list of JSON-LD-style dicts."""
        return [MutableNode(self, id).to_jsonld() for id in self]

    def add_node(self, id, type, **attr):
        super().add_node(id)
        node = MutableNode(self, id)
        node.type = type
        node.update(attr)

    def get_node(self, id):
        if id in self:
            return MutableNode(self, id)
        return None

    def remove_node(self, id, cascade=True):
        to_remove = [from_id for from_id, _ in self.in_edges_iter(id)] if cascade else ()
        super().remove_node(id)
        for from_id in to_remove:
            self.remove_node(from_id, cascade)

    def filter_nodes(self, filter):
        # TODO figure out common sorts of filters, make kwargs for them and optimize
        for id in self:
            node = MutableNode(self, id)
            if filter(node):
                yield node

    def add_named_edge(self, from_id, to_id, from_name, to_name):
        assert all(
            data.get('from_name') != from_name for _, _, data
            in self.out_edges_iter(from_id, data=True)
        ), 'Out-edge names must be unique on the node'
        self.add_edge(from_id, to_id, from_name=from_name, to_name=to_name)

    def remove_named_edge(self, from_id, from_name):
        try:
            to_id = next(
                to_id for _, to_id, data
                in self.out_edges_iter(from_id, data=True)
                if data.get('from_name') == from_name
            )
            self.remove_edge(from_id, to_id)
        except StopIteration:
            pass

    def resolve_named_out_edge(self, from_id, from_name):
        try:
            return next(
                MutableNode(self, to_id) for _, to_id, data
                in self.out_edges_iter(from_id, data=True)
                if data.get('from_name') == from_name
            )
        except StopIteration:
            return None

    def resolve_named_in_edges(self, to_id, to_name):
        return [
            MutableNode(self, from_id) for from_id, _, data
            in self.in_edges_iter(to_id, data=True)
            if data.get('to_name') == to_name
        ]

    def named_out_edges(self, from_id):
        return {
            data['from_name']: MutableNode(self, to_id) for _, to_id, data
            in self.out_edges_iter(from_id, data=True)
            if data.get('from_name') is not None
        }

    def named_in_edges(self, to_id):
        in_edges = {}
        for from_id, _, data in self.in_edges_iter(to_id, data=True):
            to_name = data.get('to_name')
            if to_name is not None:
                in_edges.setdefault(to_name, []).append(MutableNode(self, from_id))
        return in_edges

    def __bool__(self):
        return bool(len(self))


class MutableNode:
    """Convenience wrapper around a node in a MutableGraph.
    """

    def __init__(self, graph, id):
        self._id = id
        self._graph = graph

    @property
    def id(self):
        return self._id

    @property
    def attrs(self):
        return self._graph.node[self._id]

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

        If `key` corresponds to a plain attribute in the SHARE schema, return that attribute's value.
        If `key` corresponds to an outgoing edge, return a MutableNode for the node pointed to.
        If `key` corresponds to an incoming edge, return a list of MutableNodes pointing at this one.
        """
        # TODO exclude fields not in the SHARE schema
        field = self.model._meta.get_field(key)
        if field.is_relation:
            assert field.many_to_one or field.one_to_many
            if field.many_to_one:
                return self._graph.resolve_named_out_edge(self.id, field.name)
            if field.one_to_many:
                return self._graph.resolve_named_in_edges(self.id, field.name)
        return self.attrs.get(key)

    def __setitem__(self, key, value):
        # TODO exclude fields not in the SHARE schema
        field = self.model._meta.get_field(key)
        if field.is_relation:
            assert field.many_to_one
            to_id = value.id if hasattr(value, 'id') else value
            self._graph.remove_named_edge(self.id, field.name)
            self._graph.add_named_edge(self.id, to_id, field.name, field.remote_field.name)
        else:
            self.attrs[key] = value

    def __delitem__(self, key):
        field = self.model._meta.get_field(key)
        if field.is_relation:
            assert field.many_to_one
            self._graph.remove_named_edge(self.id, field.name)
        else:
            del self.attrs[key]

    def update(self, dict):
        for k, v in dict.items():
            self[k] = v

    def to_jsonld(self, ref=False):
        ld_node = {
            '@id': self.id,
            '@type': self.type,
        }
        if not ref:
            ld_node.update(self.attrs)
            for from_name, node in self._graph.named_out_edges(self.id).items():
                ld_node[from_name] = node.to_jsonld(ref=True)
            for to_name, nodes in self._graph.named_in_edges(self.id).items():
                ld_node[to_name] = [n.to_jsonld(ref=True) for n in sorted(nodes, key=lambda n: n.id)]
        return ld_node

    def __eq__(self, other):
        return other is not None and other._graph is self._graph and other.id == self.id
