from enum import Enum, auto
from operator import attrgetter

import networkx as nx
import pendulum
import uuid

from share.exceptions import ShareException
from share.legacy_normalize.schema import ShareV2Schema
from share.legacy_normalize.schema.exceptions import SchemaKeyError
from share.legacy_normalize.schema.shapes import AttributeDataType, RelationShape
from share.util import TopologicalSorter


class MutableGraphError(ShareException):
    pass


class PrivateNodeAttrs(Enum):
    TYPE = auto()


class EdgeAttrs(Enum):
    FROM_NAME = auto()
    TO_NAME = auto()


def resolve_field(type_name, field_name):
    try:
        return ShareV2Schema().get_field(type_name, field_name)
    except SchemaKeyError:
        return None


# TODO: ImmutableGraph (don't allow mutation and error on non-existent attr/relation)

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

    @classmethod
    def from_jsonld(cls, nodes):
        """Create a mutable graph from a list of JSON-LD-style dicts.
        """
        # TODO: recognize pids in workidentifier and agentidentifier, move to @id
        central_node_id = None
        if isinstance(nodes, dict):
            central_node_id = nodes.get('central_node_id', None)
            nodes = nodes['@graph']
        graph = cls()
        if central_node_id:
            graph.central_node_id = central_node_id

        for n in nodes:
            node_id, node_type = None, None
            attrs = {}
            for k, v in n.items():
                if k == '@id':
                    node_id = v
                elif k == '@type':
                    node_type = v
                elif isinstance(v, dict) and k != 'extra':
                    graph.add_node(v['@id'], v['@type'])
                    attrs[k] = v['@id']
                elif isinstance(v, list):
                    pass  # Don't bother with incoming edges, let the other node point here
                else:
                    attrs[k] = v
            if not node_id or not node_type:
                raise MutableGraphError('Nodes must have id and type')
            graph.add_node(node_id, node_type, attrs)
        return graph

    def __init__(self):
        super().__init__()
        self.changed = False
        self.central_node_id = None

    def to_jsonld(self, in_edges=True):
        """Return a dictionary with '@graph' and 'central_node_id' keys that will serialize
        to json-ld conforming with the SHARE schema

        in_edges (boolean): Include lists of incoming edges. Default True.
        """
        return {
            'central_node_id': self.central_node_id,
            '@graph': [
                node.to_jsonld(in_edges=in_edges)
                for node in self.topologically_sorted()
            ],
        }

    def add_node(self, node_id, node_type, attrs=None):
        """Create a node in the graph.

        node_id (hashable): Unique node ID. If None, generate a random ID.
        node_type (str): The node's @type value
        attrs: Dictionary of attributes or relations corresponding to fields on the node's model

        Returns a MutableNode wrapper for the new node.
        """
        if node_type is None:
            raise MutableGraphError('Must provide `node_type` to MutableGraph.add_node')
        self.changed = True

        if node_id is None:
            node_id = '_:{}'.format(uuid.uuid4())

        super().add_node(node_id)
        return MutableNode(self, node_id, node_type, attrs)

    def get_node(self, node_id):
        """Get a node by ID.

        node_id (hashable): Unique node ID

        Returns a MutableNode wrapper for the node, or None.
        """
        if node_id in self:
            return MutableNode(self, node_id)
        return None

    def remove_node(self, node_id, cascade=True):
        """Remove a node and its incoming/outgoing edges.

        node_id (hashable): Unique node ID
        cascade (boolean): Also remove nodes with edges which point to this node. Default True.
        """
        self.changed = True

        to_remove = list(self.predecessors(node_id)) if cascade else []
        super().remove_node(node_id)
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

    def filter_type(self, node_type):
        # TODO make a sort of index dict, mapping type to nodes
        return self.filter_nodes(lambda n: n.type == node_type.lower())

    def filter_by_concrete_type(self, concrete_type):
        # TODO make a sort of index dict, mapping concrete_type to nodes
        lower_concrete_type = concrete_type.lower()
        return self.filter_nodes(lambda n: n.concrete_type == lower_concrete_type)

    def add_named_edge(self, from_id, to_id, from_name, to_name):
        """Add a named edge.

        from_id (hashable): Unique ID for the node this edge comes from
        to_id (hashable): Unique ID for the node this edge points to
        from_name (str): Name of the edge on its 'from' node (must be unique on the node)
        to_name (str): Name of the edge on its 'to' node
        """
        if any(data.get(EdgeAttrs.FROM_NAME) == from_name
               for _, _, data in self.out_edges(from_id, data=True)):
            raise MutableGraphError('Out-edge names must be unique on the node')

        self.changed = True

        self.add_edge(from_id, to_id)
        self.edges[from_id, to_id][EdgeAttrs.FROM_NAME] = from_name
        self.edges[from_id, to_id][EdgeAttrs.TO_NAME] = to_name

    def remove_named_edge(self, from_id, from_name):
        """Remove a named edge.

        from_id (hashable): Unique ID for the node this edge comes from
        from_name (str): Name of the edge on its 'from' node
        """
        self.changed = True
        try:
            to_id = next(
                to_id for _, to_id, data
                in self.out_edges(from_id, data=True)
                if data.get(EdgeAttrs.FROM_NAME) == from_name
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
                if data.get(EdgeAttrs.FROM_NAME) == from_name
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
            if data.get(EdgeAttrs.TO_NAME) == to_name
        ]

    def named_out_edges(self, from_id):
        """Get all outgoing named edges from a node.

        from_id (hashable): Unique node ID

        Returns dict with:
            keys: `from_name` of each outgoing edge
            values: MutableNode wrapper for the node each edge points to
        """
        return {
            data[EdgeAttrs.FROM_NAME]: MutableNode(self, to_id) for _, to_id, data
            in self.out_edges(from_id, data=True)
            if data.get(EdgeAttrs.FROM_NAME) is not None
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
            to_name = data.get(EdgeAttrs.TO_NAME)
            if to_name is not None:
                in_edges.setdefault(to_name, []).append(MutableNode(self, from_id))
        return in_edges

    def merge_nodes(self, from_node, into_node):
        """Merge a nodes attrs and edges into another node.
        """
        if from_node.concrete_type != into_node.concrete_type:
            raise MutableGraphError('Cannot merge nodes of different types')

        self.changed = True

        # into_node will have the more specific typ
        if from_node.schema_type.distance_from_concrete_type > into_node.schema_type.distance_from_concrete_type:
            from_node, into_node = into_node, from_node

        self._merge_node_attrs(from_node, into_node)
        self._merge_in_edges(from_node, into_node)
        self._merge_out_edges(from_node, into_node)

        from_node.delete(cascade=False)

    def topologically_sorted(self):
        return TopologicalSorter(
            sorted(self, key=attrgetter('id')),
            dependencies=lambda n: sorted(self.successors(n.id)),
            key=attrgetter('id'),
        ).sorted()

    def __iter__(self):
        return (MutableNode(self, node_id) for node_id in super().__iter__())

    def __contains__(self, n):
        if isinstance(n, MutableNode):
            n = n.id
        return super().__contains__(n)

    def __bool__(self):
        return bool(len(self))

    def _merge_node_attrs(self, from_node, into_node):
        into_attrs = into_node.attrs()
        for k, new_val in from_node.attrs().items():
            if k in into_attrs:
                old_val = into_attrs[k]
                if new_val == old_val:
                    continue

                field = resolve_field(into_node.type, k)
                if getattr(field, 'data_type', None) == AttributeDataType.DATETIME:
                    new_val = max(pendulum.parse(new_val), pendulum.parse(old_val)).isoformat()
                else:
                    new_val = self._merge_value(new_val, old_val)
            into_node[k] = new_val

    def _merge_value(self, value_a, value_b):
        # use the longer value, or the first alphabetically if they're the same length
        return sorted([value_a, value_b], key=lambda x: (-len(str(x)), str(x)))[0]

    def _merge_in_edges(self, from_node, into_node):
        for in_edge_name, source_nodes in self.named_in_edges(from_node.id).items():
            inverse_relation = resolve_field(from_node.type, in_edge_name).inverse_relation
            for source_node in source_nodes:
                source_node[inverse_relation] = into_node

    def _merge_out_edges(self, from_node, into_node):
        into_edges = self.named_out_edges(into_node.id)
        for edge_name, from_target in self.named_out_edges(from_node.id).items():
            into_target = into_edges.get(edge_name)
            if from_target != into_target:
                self.merge_nodes(from_target, into_target)

    def get_central_node(self, guess=False):
        if guess and self.central_node_id is None:
            self._guess_central_node()
        return self.get_node(self.central_node_id)

    def _guess_central_node(self):
        # use a heuristic to guess the "central" node, when it's not given
        # (the whole idea of guessing here is a hack to handle old data --
        # hopefully we can get away from it eventually)

        def centrality_heuristic(work_node):
            # return a tuple of numbers (and booleans), where
            # higher numbers (including `True`s) => more likely central
            has_identifiers = bool(work_node['identifiers'])
            has_contributor_info = bool(work_node['agent_relations'])
            how_much_total_info = (
                len(work_node.attrs())
                + len(self.in_edges(work_node.id))
                + len(self.out_edges(work_node.id))
            )
            how_much_contributor_info = len(work_node['agent_relations'])
            has_parent_work = any(
                relation.type == 'ispartof'
                for relation in work_node['outgoing_creative_work_relations']
            )
            return (
                has_identifiers,
                has_contributor_info,
                how_much_total_info,
                how_much_contributor_info,
                has_parent_work,
            )

        work_nodes = self.filter_by_concrete_type('abstractcreativework')
        if work_nodes:
            # get the work node with the most attrs+relations
            work_nodes.sort(key=centrality_heuristic, reverse=True)
            if (
                len(work_nodes) > 1
                and centrality_heuristic(work_nodes[0]) == centrality_heuristic(work_nodes[1])
            ):
                raise MutableGraphError(f'cannot guess central node -- multiple candidates ({work_nodes[0].id}, {work_nodes[1].id})')
            central_node = work_nodes[0]
            self.central_node_id = central_node.id


class MutableNode:
    """Convenience wrapper around a node in a MutableGraph.
    """

    def __new__(cls, graph, node_id, *args, **kwargs):
        if node_id not in graph:
            return graph.add_node(node_id, *args, **kwargs)
        return super().__new__(cls)

    def __init__(self, graph, node_id, type_name=None, attrs=None):
        self.__graph = graph
        self.__id = node_id
        self.__attrs = graph.nodes[node_id]
        if type_name:
            self.type = type_name
        if attrs:
            self.update(attrs)

    @property
    def id(self):
        return self.__id

    @property
    def graph(self):
        return self.__graph

    @property
    def type(self):
        return self.__attrs[PrivateNodeAttrs.TYPE]

    @type.setter
    def type(self, value):
        self.graph.changed = True

        schema_type = ShareV2Schema().get_type(value)
        self.__attrs.update({
            PrivateNodeAttrs.TYPE: schema_type.name.lower(),
        })

    @property
    def concrete_type(self):
        return self.schema_type.concrete_type.lower()

    @property
    def schema_type(self):
        return ShareV2Schema().get_type(self.type)

    def attrs(self):
        return {
            k: v for k, v in self.__attrs.items()
            if not isinstance(k, PrivateNodeAttrs)
        }

    def relations(self, in_edges=True, jsonld=False):
        relations = {}
        for from_name, node in self.graph.named_out_edges(self.id).items():
            relations[from_name] = node.to_jsonld(ref=True) if jsonld else node
        if in_edges:
            for to_name, nodes in self.graph.named_in_edges(self.id).items():
                sorted_nodes = sorted(nodes, key=lambda n: n.id)
                relations[to_name] = [n.to_jsonld(ref=True) for n in sorted_nodes] if jsonld else sorted_nodes
        return relations

    def __getitem__(self, key):
        """Get an attribute value or related node(s).

        key (str): Name of an attribute, outgoing named edge, or incoming named edge.

        If key is the name of a plain attribute in the SHARE schema, return that attribute's value.
        If key is the name of an outgoing edge, return a MutableNode that edge points to
        If key is the name of incoming edges, return a list of MutableNodes those edges come from
        """
        field = resolve_field(self.type, key)
        if field and field.is_relation and field.name != 'extra':
            if field.relation_shape == RelationShape.MANY_TO_ONE:
                return self.graph.resolve_named_out_edge(self.id, field.name)
            if field.relation_shape == RelationShape.ONE_TO_MANY:
                return self.graph.resolve_named_in_edges(self.id, field.name)
            if field.relation_shape == RelationShape.MANY_TO_MANY:
                m2m_related_nodes = self._resolve_many_to_many(
                    field.through_concrete_type,
                    field.incoming_through_relation,
                    field.outgoing_through_relation,
                )
                is_reflexive = (field.related_concrete_type.lower() == self.concrete_type)
                if is_reflexive:
                    # for a reflexive m2m, include nodes related in either direction
                    m2m_related_nodes.update(self._resolve_many_to_many(
                        field.through_concrete_type,
                        # outgoing/incoming swapped
                        field.outgoing_through_relation,
                        field.incoming_through_relation,
                    ))
                return list(m2m_related_nodes)

            raise MutableGraphError('Only many-to-one, one-to-many, and non-reflexive many-to-many relations allowed')
        return self.__attrs.get(field.name if field else key)

    def _resolve_many_to_many(self, through_concrete_type, incoming_through_relation, outgoing_through_relation):
        incoming_edge_name = ShareV2Schema().get_field(
            through_concrete_type,
            incoming_through_relation
        ).inverse_relation

        through_nodes = self.graph.resolve_named_in_edges(self.id, incoming_edge_name)

        return set(
            self.graph.resolve_named_out_edge(through_node.id, outgoing_through_relation)
            for through_node in through_nodes
        )

    def __setitem__(self, key, value):
        """Set an attribute value or add an outgoing named edge.

        key (str): Name of an attribute or an outgoing edge.

        If key is the name of a plain attribute in the SHARE schema, set that attribute's value.
        If key is the name of an outgoing edge, expect `value` to be a node ID or a MutableNode. Add an edge from this node to that one.
        If key is the name of incoming edges, raise an error.

        If value is None, same as `del node[key]`
        """
        self.graph.changed = True

        field = resolve_field(self.type, key)
        field_name = field.name if field else key

        if value is None:
            del self[field_name]
            return

        if field and field.is_relation:
            if field.relation_shape != RelationShape.MANY_TO_ONE:
                raise MutableGraphError('Can set only many-to-one relations')
            to_id = value.id if hasattr(value, 'id') else value
            self.graph.remove_named_edge(self.id, field_name)
            self.graph.add_named_edge(self.id, to_id, field_name, field.inverse_relation)
        else:
            self.__attrs[field_name] = value

    def __delitem__(self, key):
        """Delete an attribute value or outgoing named edge.

        key (str): Name of an attribute or an outgoing edge.

        If key is the name of an attribute in the SHARE schema, delete that attribute from this node.
        If key is the name of an outgoing edge, remove that edge.
        If key is the name of incoming edges, raise an error.
        """
        self.graph.changed = True

        field = resolve_field(self.type, key)
        field_name = field.name if field else key

        if field and field.is_relation:
            if field.relation_shape != RelationShape.MANY_TO_ONE:
                raise MutableGraphError('Can delete only many-to-one relations')
            self.graph.remove_named_edge(self.id, field_name)
        elif field_name in self.__attrs:
            del self.__attrs[field_name]

    def update(self, attrs):
        for k, v in attrs.items():
            self[k] = v

    def delete(self, cascade=True):
        """Remove this node from its graph.

        cascade (boolean): Also remove nodes with edges which point to this node. Default True.
        """
        self.graph.changed = True
        self.graph.remove_node(self.id, cascade)
        self.__graph = None

    def to_jsonld(self, ref=False, in_edges=False):
        ld_node = {
            '@id': self.id,
            '@type': self.type,
        }
        if not ref:
            ld_node.update(self.relations(in_edges=in_edges, jsonld=True))
            ld_node.update(self.attrs())
        return ld_node

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.graph is self.graph and other.id == self.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return '<{} id({}) type({})>'.format(self.__class__.__name__, self.id, self.type)
    __repr__ = __str__
