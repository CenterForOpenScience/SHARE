from .base import MatchingStrategy

from share import models


def equal_not_none(lhs, rhs):
    return None not in (lhs, rhs) and lhs == rhs


class IndexByAttrs:
    def __init__(self, attr_names):
        self.attr_names = attr_names
        self._index = {}

    def node_key(self, node):
        return tuple(node[a] for a in self.attr_names)

    def add_nodes(self, nodes):
        for node in nodes:
            key = self.node_key(node)
            if None not in key:
                self._index.setdefault(key, set()).add(node)

    def get_matches(self, node):
        key = self.node_key(node)
        matches = self._index.get(key, set())
        return matches.difference([node])


class GraphStrategy(MatchingStrategy):
    def __init__(self, graph, **kwargs):
        super().__init__(**kwargs)
        self.graph = graph

    def initial_pass(self, nodes):
        pass

    def match_by_attrs(self, nodes, model, attr_names, allowed_models):
        graph_nodes = self._graph_nodes(model, allowed_models)

        attr_index = IndexByAttrs(attr_names)
        attr_index.add_nodes(graph_nodes)

        for node in nodes:
            matches = attr_index.get_matches(node)
            if matches:
                self.add_matches(node, matches)

    def match_by_many_to_one(self, nodes, model, relation_names, allowed_models):
        self.match_by_attrs(nodes, model, relation_names, allowed_models)

    def match_by_one_to_many(self, nodes, model, relation_name):
        # a one-to-many can't be two-to-many
        pass

    def match_subjects(self, nodes):
        graph_nodes = self._graph_nodes(models.Subject)

        for node in nodes:
            matches = [
                n for n in graph_nodes
                if n != node
                and n['parent'] == node['parent']
                and n['central_synonym'] == node['central_synonym']
                and (equal_not_none(n['uri'], node['uri']) or equal_not_none(n['name'], node['name']))
            ]
            self.add_matches(node, matches)

    def match_agent_work_relations(self, nodes):
        # no special case when looking within a graph
        pass

    def _graph_nodes(self, model, allowed_models=None):
        if allowed_models is None:
            return self.graph.filter_by_concrete_type(model._meta.concrete_model._meta.model_name)
        else:
            allowed_model_names = {
                allowed_model._meta.model_name.lower()
                for allowed_model in allowed_models
            }
            return filter(
                lambda n: n.type in allowed_model_names,
                self.graph,
            )
