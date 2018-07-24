from .base import MatchingStrategy

from share import models


class GraphStrategy(MatchingStrategy):
    def __init__(self, graph, **kwargs):
        super().__init__(**kwargs)
        self.graph = graph

    def initial_pass(self, nodes):
        pass

    def match_by_attrs(self, nodes, model, attr_names, allowed_models):
        graph_nodes = self._graph_nodes(model, allowed_models)

        for node in nodes:
            matches = [
                n for n in graph_nodes
                if n != node and all(n[a] == node[a] for a in attr_names)
            ]
            self.add_matches(node, matches)

    def match_by_many_to_one(self, nodes, model, relation_names, allowed_models):
        self.match_by_attrs(nodes, model, relation_names, allowed_models)

    def match_by_one_to_many(self, nodes, model, relation_name):
        # a one-to-many can't be two-to-many
        pass

    def match_subjects(self, nodes):
        self.match_by_attrs(nodes, models.Subject, ('central_synonym', 'uri'), None)
        self.match_by_attrs(nodes, models.Subject, ('central_synonym', 'name'), None)

    def match_agent_work_relations(self, nodes):
        # no special case when looking within a graph
        pass

    def _graph_nodes(self, model, allowed_models=None):
        if allowed_models is None:
            return self.graph.filter_by_concrete_model(model._meta.concrete_model)
        else:
            return filter(
                lambda n: n.model in allowed_models,
                self.graph,
            )
