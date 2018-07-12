import logging

from django.db.models import Q

from share.exceptions import MergeRequired
from share.util import IDObfuscator, InvalidID
from share.util.graph import MutableNode

__all__ = ('GraphDisambiguator', )

logger = logging.getLogger(__name__)


class GraphDisambiguator:

    def __init__(self, source=None):
        self.source = source

    def find_instances(self, graph):
        # for each node in the graph, look for a matching instance in the database
        # TODO: what happens when two (apparently) non-duplicate nodes disambiguate to the same instance?

        # Sort by type and id as well to get consistent sorting
        nodes = sorted(graph, key=lambda n: (self._disambiguweight(n), n.type, n.id), reverse=True)

        instance_map = {}

        changed = True
        while changed:
            changed = False

            for n in nodes:
                if n in instance_map:
                    continue
                instance = self._instance_for_node(n, instance_map)
                if instance:
                    changed = True
                    instance_map[n] = instance
                    logger.debug('Disambiguated %s to %s', n, instance)
        return instance_map

    def _disambiguweight(self, node):
        # Models with exactly 1 foreign key field (excluding those added by
        # ShareObjectMeta) are disambiguated first, because they might be used
        # to uniquely identify the object they point to. Then do the models with
        # 0 FKs, then 2, 3, etc.
        ignored = {'same_as', 'extra'}
        fk_count = sum(
            1
            for f in node.model._meta.get_fields()
            if f.editable and (f.many_to_one or f.one_to_one) and f.name not in ignored
        )
        return fk_count if fk_count == 1 else -fk_count

    def _instance_for_node(self, node, instance_map):
        model = node.model
        concrete_model = model._meta.concrete_model

        if not node.id.startswith('_:'):
            try:
                return IDObfuscator.resolve(node.id)
            except (InvalidID, model.DoesNotExist):
                pass

        if concrete_model.__name__ == 'Subject':
            return self._instance_for_subject(node)

        info = DisambiguationInfo(node)
        if not info.all and not info.any:
            return None

        all_query = Q()
        for k, v in info.all:
            k, v = self._query_pair(k, v, instance_map)
            if k and v:
                all_query &= Q(**{k: v})
            else:
                return None

        queries = []
        for k, v in info.any:
            k, v = self._query_pair(k, v, instance_map)
            if k and v:
                queries.append(all_query & Q(**{k: v}))

        if (info.all and not all_query.children) or (info.any and not queries):
            return None

        if info.matching_types:
            all_query &= Q(type__in=info.matching_types)

        constrain = [Q()]
        if hasattr(model, '_typedmodels_type'):
            constrain.append(Q(type__in=model.get_types()))
            constrain.append(Q(type=model._typedmodels_type))

        for q in constrain:
            sql, params = zip(*[concrete_model.objects.filter(all_query & query & q).query.sql_with_params() for query in queries or [Q()]])
            found = list(concrete_model.objects.raw(' UNION '.join('({})'.format(s) for s in sql) + ' LIMIT 2;', sum(params, ())))

            if not found:
                logger.debug('No %ss found for %s %s', concrete_model, all_query & q, queries)
                return None
            if len(found) == 1:
                return found[0]
            if all_query.children:
                logger.warning('Multiple %ss returned for %s (The main query) bailing', concrete_model, all_query)
                break
            if all('__' in str(query) for query in queries):
                logger.warning('Multiple %ss returned for %s (The any query) bailing', concrete_model, queries)
                break

        logger.error('Could not disambiguate %s. Too many results found from %s %s', model, all_query, queries)
        raise MergeRequired('Multiple {0}s found'.format(model), model, queries)

    def _instance_for_subject(self, node):
        # Subject disambiguation is a bit weird: Match taxonomy AND (uri OR name)
        model = node.model
        qs = None
        if node['central_synonym'] is None:
            # Central taxonomy
            qs = model.objects.filter(central_synonym__isnull=True)
        else:
            # Custom taxonomy
            if self.source:
                qs = model.objects.filter(taxonomy__source=self.source)

        if not qs:
            return None

        uri = node['uri']
        if uri:
            try:
                return qs.get(uri=uri)
            except model.DoesNotExist:
                pass

        name = node['name']
        if name:
            try:
                return qs.get(name=name)
            except model.DoesNotExist:
                pass
        logger.debug('Could not disambiguate subject %s', node)
        return None

    def _query_pair(self, key, value, instance_map):
        if isinstance(value, MutableNode):
            instance = instance_map.get(value)
            if not instance:
                return (None, None)
            return ('{}__id'.format(key), instance.id)
        return (key, value)


class DisambiguationInfo:
    def __init__(self, node):
        self._node = node
        self.all = self._all()
        self.any = self._any()
        self.matching_types = self._matching_types()

    def _all(self):
        try:
            all = self._node.model.Disambiguation.all
        except AttributeError:
            return ()
        values = tuple((f, v) for f in all for v in self._field_values(f))
        assert len(values) == len(all), 'Wrong number of values: {} for "all": {}'.format(values, all)
        return values

    def _any(self):
        try:
            any = self._node.model.Disambiguation.any
        except AttributeError:
            return ()
        return tuple((f, v) for f in any for v in self._field_values(f))

    def _matching_types(self):
        model = self._node.model
        try:
            constrain_types = model.Disambiguation.constrain_types
        except AttributeError:
            constrain_types = False
        if not constrain_types:
            return None

        # list of all subclasses and superclasses of node.model that could be the type of a node
        # TODO: stop using typedmodels like this -- make `@type` the concrete model and add a field for
        # subtype (e.g. {'@type': 'CreativeWork', 'subtype': 'Preprint'})
        # But not 'subtype'. Something better.
        concrete_model = model._meta.concrete_model
        if concrete_model is model:
            type_names = [model._meta.label_lower]
        else:
            subclasses = model.get_types()
            superclasses = [m._meta.label_lower for m in model.__mro__ if issubclass(m, concrete_model) and m._meta.proxy]
            type_names = subclasses + superclasses
        return set(type_names)

    def _field_values(self, field_name):
        value = self._node[field_name]
        if isinstance(value, list):
            yield from value
        else:
            if value != '':
                yield value
