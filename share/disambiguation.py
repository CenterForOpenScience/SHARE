import logging

from django.core.exceptions import ValidationError

from share import models
from share.util import DictHashingDict
from share.util import IDObfuscator

__all__ = ('GraphDisambiguator', )

logger = logging.getLogger(__name__)


class GraphDisambiguator:
    def __init__(self):
        self._cache = self.NodeCache()

    def prune(self, change_graph):
        # for each node in the graph, compare to each other node and remove duplicates
        # compare based on type (one is a subclass of the other), attrs (exact matches), and relations
        return self._disambiguate(change_graph, False)

    def find_instances(self, change_graph):
        # for each node in the graph, look for a matching instance in the database 
        # TODO: is it safe to assume no duplicates? right now, prunes duplicates again
        # TODO: what happens when two (apparently) non-duplicate nodes disambiguate to the same instance?
        return self._disambiguate(change_graph, True)

    def _disambiguate(self, change_graph, find_instances):
        changed = True
        nodes = sorted(change_graph.nodes, key=self._disambiguweight, reverse=True)

        while changed:
            changed = False
            # TODO update affected nodes after changes instead of rebuilding the cache every loop
            self._cache.clear()

            for n in tuple(nodes):
                if n.is_merge or (find_instances and n.instance):
                    continue
                matches = self._cache.get_matches(n)
                if len(matches) > 1:
                    # TODO?
                    raise NotImplementedError('Multiple matches that apparently didn\'t match each other?\nNode: {}\nMatches: {}'.format(node, matches))

                if matches:
                    # remove duplicates within the graph
                    match = matches.pop()
                    if n.model != match.model and issubclass(n.model, match.model):
                        # remove the node with the less-specific class
                        logger.debug('Found duplicate! Keeping {}, pruning {}'.format(n, match))
                        change_graph.replace(match, n)
                        self._cache.remove(match)
                        nodes.remove(match)
                        self._cache.add(n)
                    else:
                        logger.debug('Found duplicate! Keeping {}, pruning {}'.format(match, n))
                        nodes.remove(n)
                        change_graph.replace(n, match)
                    changed = True
                    continue

                if find_instances:
                    # look for matches in the database
                    instance = self._instance_for_node(n)
                    if isinstance(instance, list):
                        # TODO after merging is fixed, add mergeaction change to graph
                        raise NotImplementedError()
                    if instance:
                        changed = True
                        n.instance = instance
                        logger.debug('Disambiguated {} to {}'.format(n, instance))

                self._cache.add(n)

    def _disambiguweight(self, node):
        # Models with exactly 1 foreign key field (excluding those added by
        # ShareObjectMeta) are disambiguated first, because they might be used
        # to uniquely identify the object they point to. Then do the models with
        # 0 FKs, then 2, 3, etc.
        ignored = {'same_as', 'extra'}
        fk_count = sum(1 for f in node.model._meta.get_fields() if f.editable and (f.many_to_one or f.one_to_one) and f.name not in ignored)
        return fk_count if fk_count == 1 else -fk_count

    def _instance_for_node(self, node):
        info = self._cache.get_info(node)
        filter = {
            # TODO relations
            **query['attrs']
        }
        concrete_model = node.model._meta.concrete_model
        if concrete_model is not node.model:
            filter['type__in'] = self._matching_type_names(node)

        found = set(concrete_model.objects.filter(**filter))
        if len(found) == 1:
            return found.pop()
        logger.warn('Multiple {}s returned for {}'.format(concrete_model, filter))
        return list(found)

    def _matching_type_names(self, node):
        # list of all subclasses and superclasses of node.model
        fmt = lambda model: 'share.{}'.format(model._meta.model_name)
        concrete_model = node.model._meta.concrete_model
        if concrete_model is node.model:
            type_names = [fmt(node.model)]
        else:
            type_names = node.model.get_types() + [fmt(m) for m in node.model.__mro__ if issubclass(m, concrete_model) and m._meta.proxy]
        return set(type_names)


    class NodeCache:
        def __init__(self):
            self._node_cache = {}
            self._info_cache = {}

        def clear(self):
            self._node_cache.clear()
            self._info_cache.clear()

        def get_info(self, node):
            try:
                return self._info_cache[node]
            except KeyError:
                info = self.NodeInfo(node)
                self._info_cache[node] = info
                return info

        def add(self, node):
            info = self.get_info(node)
            model_cache = self._node_cache.setdefault(node.model._meta.concrete_model, DictHashingDict())
            if info.any:
                all_cache = model_cache.setdefault(info.all, DictHashingDict())
                for item in info.any.items():
                    all_cache.setdefault(item, []).append(node)
            elif info.all:
                model_cache.setdefault(info.all, []).append(node)
            else:
                logger.debug('Nothing to disambiguate on. Ignoring node {}'.format(node))

        def remove(self, node):
            info = self.get_info(node)
            try:
                all_cache = self._node_cache[node.model._meta.concrete_model][info.all]
                if info.any:
                    for item in info.any.items():
                        all_cache[item].remove(node)
                else:
                    all_cache.remove(node)
            except (KeyError, ValueError) as ex:
                raise ValueError('Could not remove node from cache: Node {} not found!'.format(node)) from ex

        def get_matches(self, node):
            info = self.get_info(node)
            matches = set()
            try:
                model_cache = self._node_cache[node.model._meta.concrete_model]
                matches_all = model_cache[info.all]
                if info.any:
                    for item in info.any.items():
                        matches.update(matches_all.get(item, []))
                elif info.all:
                    matches.update(matches_all)
                return [m for m in matches if m != node and issubclass(m.model, node.model) or issubclass(node.model, m.model)]
            except KeyError:
                return []

        # TODO better name
        class NodeInfo:
            def __init__(self, node):
                self._node = node
                self.all = self._all()
                self.any = self._any()

            def _all(self):
                try:
                    all = self._node.model.Disambiguation.all
                except AttributeError:
                    return {}
                values = {f: self._field_value(f) for f in all}
                missing = [f for f, v in values.items() if v is None]
                if missing:
                    logger.debug('Missing required fields for disambiguation!\nNode: {}\nMissing: {}'.format(self._node, missing))
                    return {}
                return values

            def _any(self):
                try:
                    any = self._node.model.Disambiguation.any
                except AttributeError:
                    return {}
                return {f: self._field_value(f, nested=True) for f in any}

            def _field_value(self, field_name, nested=False):
                if isinstance(field_name, (list, tuple)):
                    if nested:
                        return tuple(self._field_value(f) for f in field_name)
                    else:
                        raise ValueError('Disambiguation info cannot be nested for `all`, and only one level deep for `any`.')

                field = self._node.model._meta.get_field(field_name)
                if field.is_relation:
                    if field.one_to_many:
                        edges = self._node.related(name=field_name, forward=False)
                        return tuple(e.subject for e in edges)
                    elif field.many_to_many:
                        # TODO
                        raise NotImplementedError()
                else:
                    if field_name not in self._node.attrs:
                        return None
                    value = self._node.attrs[field.name]
                    if value == '':
                        return None
                    return value
