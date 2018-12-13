import abc


class MatchingStrategy(abc.ABC):
    def __init__(self):
        self._matches = {}

    def get_matches(self, node):
        return self._matches.get(node, frozenset())

    def add_match(self, node, match):
        self._matches.setdefault(node, set()).add(match)

    def add_matches(self, node, matches):
        self._matches.setdefault(node, set()).update(matches)

    def has_matches(self, node):
        return bool(self._matches.get(node))

    def clear_matches(self):
        self._matches = {}

    @abc.abstractmethod
    def initial_pass(self, nodes):
        raise NotImplementedError

    @abc.abstractmethod
    def match_by_attrs(self, nodes, model, attr_names, allowed_models):
        raise NotImplementedError

    @abc.abstractmethod
    def match_by_many_to_one(self, nodes, model, relation_names, allowed_models):
        raise NotImplementedError

    @abc.abstractmethod
    def match_by_one_to_many(self, nodes, model, relation_name):
        raise NotImplementedError

    @abc.abstractmethod
    def match_subjects(self, nodes):
        raise NotImplementedError

    @abc.abstractmethod
    def match_agent_work_relations(self, nodes):
        raise NotImplementedError
