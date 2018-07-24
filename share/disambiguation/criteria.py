import abc


class MatchingCriterion(abc.ABC):
    @abc.abstractmethod
    def match(self, strategy, nodes, model):
        raise NotImplementedError

    @abc.abstractmethod
    def model_dependencies(self, model):
        raise NotImplementedError


class MatchByAttrs(MatchingCriterion):
    def __init__(self, *attr_names, allowed_models=None):
        self.attr_names = attr_names
        self.allowed_models = allowed_models

    def match(self, strategy, nodes, model):
        if any(model._meta.get_field(f).is_relation for f in self.attr_names):
            raise ValueError('No relations allowed in MatchByAttrs: {}'.format(self.attr_names))

        return strategy.match_by_attrs(nodes, model, self.attr_names, self.allowed_models)

    def model_dependencies(self, model):
        return []


class MatchByManyToOne(MatchingCriterion):
    def __init__(self, *relation_names, constrain_types=False):
        self.relation_names = relation_names
        self.constrain_types = constrain_types

    def match(self, strategy, nodes, model):
        if not all(model._meta.get_field(f).many_to_one for f in self.relation_names):
            raise ValueError('Only many-to-one relations allowed in MatchByManyToOne: {}'.format(self.relation_names))

        if not self.constrain_types:
            allowed_models = None
        elif model is model._meta.concrete_model:
            allowed_models = [model]
        else:
            subclasses = model.get_type_classes()
            superclasses = [
                m for m in model.__mro__
                if issubclass(m, model._meta.concrete_model) and m._meta.proxy
            ]
            allowed_models = set(subclasses + superclasses)

        return strategy.match_by_many_to_one(nodes, model, self.relation_names, allowed_models)

    def model_dependencies(self, model):
        return [
            model._meta.get_field(f).related_model
            for f in self.relation_names
        ]


class MatchByOneToMany(MatchingCriterion):
    def __init__(self, relation_name):
        self.relation_name = relation_name

    def match(self, strategy, nodes, model):
        if not model._meta.get_field(self.relation_name).one_to_many:
            raise ValueError('MatchByOneToMany requires a one-to-many relation: {}'.format(self.relation_name))

        return strategy.match_by_one_to_many(nodes, model, self.relation_name)

    def model_dependencies(self, model):
        return [
            model._meta.get_field(self.relation_name).related_model
        ]


class MatchSubjects(MatchingCriterion):
    def match(self, strategy, nodes, model):
        return strategy.match_subjects(nodes)

    def model_dependencies(self, model):
        return []


class MatchAgentWorkRelations(MatchingCriterion):
    def match(self, strategy, nodes, model):
        return strategy.match_agent_work_relations(nodes)

    def model_dependencies(self, model):
        return [
            model._meta.get_field(f).related_model
            for f in ('agent', 'creative_work')
        ]
