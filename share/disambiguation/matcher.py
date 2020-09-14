from django.apps import apps

from share.exceptions import MergeRequired
from share.util import TopologicalSorter, ensure_iterable

from share.disambiguation.criteria import MatchingCriterion


class Matcher:
    def __init__(self, strategy):
        self.strategy = strategy

    def find_all_matches(self, graph):
        self.strategy.initial_pass(graph)

        for model, nodes in self._group_nodes_by_model(graph):
            for criterion in self._get_model_criteria(model):
                criterion.match(self.strategy, nodes, model)

        # for now, enforce only one match
        # TODO: remove this restriction
        single_matches = {}
        for node, matches in self.strategy._matches.items():
            if not matches:
                continue
            if len(matches) > 1:
                raise MergeRequired('Multiple matches for node {}'.format(node.id), matches)
            single_matches[node] = list(matches)[0]

        return single_matches

    def chunk_matches(self, graph):
        self.strategy.initial_pass(graph)
        yield self.strategy._matches
        self.strategy.clear_matches()

        for model, nodes in self._group_nodes_by_model(graph):
            for criteria in self._get_model_criteria(model):
                criteria.match(self.strategy, nodes, model)
            yield self.strategy._matches
            self.strategy.clear_matches()

    def _group_nodes_by_model(self, graph):
        nodes_by_model = {}
        for node in graph:
            model = apps.get_model('share', node.type)
            nodes_by_model.setdefault(model, []).append(node)

        models = list(nodes_by_model.keys())

        sorted_models = TopologicalSorter(
            models,
            lambda n: self._get_model_dependencies(n, models),
        ).sorted()

        return ((model, nodes_by_model[model]) for model in sorted_models)

    def _get_model_criteria(self, model):
        # TODO: cache?
        criteria = getattr(model, 'matching_criteria', None)
        if not criteria:
            return None
        criteria = ensure_iterable(criteria)
        if not all(isinstance(c, MatchingCriterion) for c in criteria):
            raise ValueError('{}.matching_criteria must be a MatchingCriterion instance'.format(model._meta.model_name))
        return criteria

    def _get_model_dependencies(self, model, all_models):
        criteria = self._get_model_criteria(model)
        if not criteria:
            return []
        concrete_dependencies = set(
            dep
            for c in criteria
            for dep in c.model_dependencies(model)
        )

        dependencies = [
            m for m in all_models
            if m._meta.concrete_model in concrete_dependencies
        ]
        return dependencies
