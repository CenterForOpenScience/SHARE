import logging

from django.core.exceptions import ValidationError

from share import models
from share.util import DictHashingDict
from share.util import IDObfuscator

__all__ = ('GraphDisambiguator', )

logger = logging.getLogger(__name__)


class GraphDisambiguator:
    def __init__(self):
        self._cache = DictHashingDict()
        self.__disambiguator_map = {}
        self._gather_disambiguators(Disambiguator)

    def disambiguate(self, change_graph):
        changed, nodes = True, sorted(change_graph.nodes, key=self._disambiguweight, reverse=True)

        while changed:
            changed = False

            for n in nodes:
                if n.is_merge or n.instance:
                    continue

                relations = tuple(e.related for e in sorted(n.related(backward=False), key=lambda e: e.name))
                handled = self._cache.setdefault((n.model, n.attrs, relations), n)
                if handled is not n and (n.attrs or relations):
                    nodes.remove(n)
                    change_graph.replace(n, handled)
                    continue

                instance = self.instance_for_node(n)

                if isinstance(instance, list):
                    # TODO after merging is fixed, add mergeaction change to graph
                    raise NotImplementedError()

                if instance:
                    changed = True
                    n.instance = instance
                    logger.debug('Disambiguated {} to {}'.format(n, instance))

    def instance_for_node(self, node):
        NodeDisambiguator = GenericDisambiguator
        for klass in node.model.mro():
            if klass in self.__disambiguator_map:
                NodeDisambiguator = self.__disambiguator_map[klass]
                break
            if not klass._meta.proxy:
                break
        return NodeDisambiguator(node.id, node.resolve_attrs(), node.model).find()

    def _disambiguweight(self, node):
        # Models with exactly 1 foreign key field (excluding those added by
        # ShareObjectMeta) are disambiguated first, because they might be used
        # to uniquely identify the object they point to. Then do the models with
        # 0 FKs, then 2, 3, etc.
        ignored = {'same_as', 'extra'}
        fk_count = sum(1 for f in node.model._meta.get_fields() if f.editable and (f.many_to_one or f.one_to_one) and f.name not in ignored)
        return fk_count if fk_count == 1 else -fk_count

    def _gather_disambiguators(self, base):
        for cls in base.__subclasses__():
            for model in (getattr(cls, 'FOR_MODEL', None), ) + getattr(cls, 'FOR_MODELS', tuple()):
                if not model:
                    continue
                if model in self.__disambiguator_map:
                    raise ValueError('Disambiguator {} is already registered for {}.'.format(self.__disambiguator_map[model], model))
                self.__disambiguator_map[model] = cls
            self._gather_disambiguators(cls)


class Disambiguator:

    def __init__(self, id, attrs, model):
        self.id = id
        self.model = model
        # only include attrs with truthy values
        self.attrs = {k: v for k, v in attrs.items() if v}
        self.is_blank = id.startswith('_:')
        if not self.is_blank:
            model, self.id = IDObfuscator.decode(self.id)
            assert issubclass(model, (self.model._meta.concrete_model, ))

    def disambiguate(self):
        raise NotImplementedError()

    def find(self):
        if self.id and not self.is_blank:
            return self.model._meta.concrete_model.objects.get(pk=self.id)
        return self.disambiguate()


class GenericDisambiguator(Disambiguator):

    @property
    def is_through_table(self):
        # TODO fix this...
        return 'Through' in self.model.__name__ or self.model._meta.concrete_model in {
            models.AbstractAgentWorkRelation,
            models.AbstractAgentRelation,
            models.AbstractWorkRelation,
        }

    def disambiguate(self):
        if not self.attrs:
            return None

        if self.is_through_table:
            return self._disambiguate_through()

        return self.model.objects.filter(**self.attrs).first()

    def _disambiguate_through(self):
        for unique_fields in self.model._meta.concrete_model._meta.unique_together:
            if 'type' in unique_fields and 'type' not in self.attrs:
                self.attrs['type'] = self.model._meta.label_lower

            # Don't dissambiguate through tables that don't have both sides filled out
            if any(field not in self.attrs for field in unique_fields):
                continue

            try:
                return self.model.objects.get(**{field: self.attrs[field] for field in unique_fields})
            except self.model.DoesNotExist:
                continue
        return None


class UniqueAttrDisambiguator(Disambiguator):
    @property
    def unique_attr(self):
        raise NotImplementedError()

    def not_found(self):
        return None

    def disambiguate(self):
        value = self.attrs.get(self.unique_attr)
        if not value:
            return None
        try:
            query = {self.unique_attr: value}
            return self.model.objects.get(**query)
        except self.model.DoesNotExist:
            return self.not_found()


class AgentWorkRelationDisambiguator(Disambiguator):
    FOR_MODELS = tuple(models.AgentWorkRelation.get_type_classes())

    def disambiguate(self):
        if not self.attrs.get('creative_work'):
            return None
        if not self.attrs.get('cited_as') and not self.attrs.get('agent'):
            return None
        try:
            return self.model.objects.get(**self.attrs)
        except self.model.DoesNotExist:
            return None


class WorkIdentifierDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.WorkIdentifier
    unique_attr = 'uri'


class AgentIdentifierDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.AgentIdentifier
    unique_attr = 'uri'


class TagDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.Tag
    unique_attr = 'name'


class SubjectDisambiguator(UniqueAttrDisambiguator):
    FOR_MODEL = models.Subject
    unique_attr = 'name'

    def not_found(self):
        raise ValidationError('Invalid subject: {}'.format(self.attrs['name']))


class AbstractAgentDisambiguator(Disambiguator):
    FOR_MODEL = models.AbstractAgent
    NAME_KEYS = ('given_name', 'additional_name', 'family_name', 'suffix')

    def disambiguate(self):
        if not self.attrs.get('identifiers'):
            if self.attrs.get('work_relations'):
                found = set(models.AbstractAgent.objects.filter(work_relations__id__in=self.attrs['work_relations']))
                if len(found) == 1:
                    return found.pop()
                return list(sorted(found, key=lambda x: x.pk)) or None

            if self.model == models.Person or not self.attrs.get('name'):
                return None
            try:
                # TODO Make revisit this logic
                return self.model.objects.filter(name=self.attrs['name']).first()
            except self.model.DoesNotExist:
                return None

        found = set(models.AbstractAgent.objects.filter(identifiers__id__in=self.attrs['identifiers']))

        if len(found) == 1:
            return found.pop()  # Seems to be the best way to get something out of a set
        return list(sorted(found, key=lambda x: x.pk)) or None


class AbstractCreativeWorkDisambiguator(Disambiguator):
    FOR_MODEL = models.AbstractCreativeWork

    def disambiguate(self):
        if not self.attrs.get('identifiers'):
            return None

        found = set(models.AbstractCreativeWork.objects.filter(identifiers__id__in=self.attrs['identifiers']))

        if len(found) == 1:
            return found.pop()  # Seems to be the best way to get something out of a set
        return list(sorted(found, key=lambda x: x.pk)) or None


class OrganizationDisambiguator(Disambiguator):
    FOR_MODELS = (models.Organization, models.Institution)

    def disambiguate(self):
        if not self.attrs.get('name'):
            return None
        try:
            return self.model.objects.get(name=self.attrs['name'], type__in=self.model.get_types())
        except self.model.DoesNotExist:
            return None
