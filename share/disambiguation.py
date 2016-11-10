import logging

from django.core.exceptions import ValidationError

from share import models
from share.util import DictHashingDict
from share.util import IDObfuscator

__all__ = ('GraphDisambiguator', )

logger = logging.getLogger(__name__)


class GraphDisambiguator:
    def __init__(self):
        self._node_cache = {}
        self._query_cache = {}

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
            # TODO update only affected nodes instead of rebuilding the cache every loop
            self._clear_cache()

            for n in tuple(nodes):
                if n.is_merge or (find_instances and n.instance):
                    continue
                matches = self._get_cached_matches(n)
                if len(matches) > 1:
                    # TODO?
                    raise NotImplementedError('Multiple matches that apparently didn\'t match each other?\nNode: {}\nMatches: {}'.format(node, matches))

                if matches:
                    # remove duplicates within the graph
                    match = matches[0]
                    if n.model != match.model and issubclass(n.model, match.model):
                        # remove the node with the less-specific class
                        logger.debug('Found match! Keeping {}, pruning {}'.format(n, match))
                        nodes.remove(match)
                        change_graph.replace(match, n)
                        self._uncache_node(match)
                        self._cache_node(n)
                    else:
                        logger.debug('Found match! Keeping {}, pruning {}'.format(match, n))
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

    def _disambiguweight(self, node):
        # Models with exactly 1 foreign key field (excluding those added by
        # ShareObjectMeta) are disambiguated first, because they might be used
        # to uniquely identify the object they point to. Then do the models with
        # 0 FKs, then 2, 3, etc.
        ignored = {'same_as', 'extra'}
        fk_count = sum(1 for f in node.model._meta.get_fields() if f.editable and (f.many_to_one or f.one_to_one) and f.name not in ignored)
        return fk_count if fk_count == 1 else -fk_count

    def _get_query(self, node):
        if node in self._query_cache:
            return self._query_cache[node]

        query = {
            'attrs': {},
            'relations': {}
        }

        fields = [
            node.model._meta.get_field(f)
            for f in node.model.Meta.disambiguation_fields
        ]
        for f in fields:
            if f.is_relation:
                # TODO
                pass
            else:
                if f.name not in node.attrs:
                    raise ValueError('Missing field {} for disambiguation!\nNode: {}'.format(f.name, node))
                query['attrs'][f.name] = node.attrs[f.name]

        self._query_cache[node] = query
        return query

    def _clear_cache(self, node):
        self._node_cache.clear()
        self._query_cache.clear()

    def _cache_node(self, node):
        q = self._get_query(node)
        concrete_model = node.model._meta.concrete_model
        self._node_cache.setdefault(concrete_model, DictHashingDict()).setdefault((q['attrs'], q['relations']), []).append(node)

    def _uncache_node(self, node):
        q = self._get_query(node)
        concrete_model = node.model._meta.concrete_model
        try:
            self._node_cache[concrete_model][q['attrs'], q['relations']].remove(node)
        except KeyError, ValueError:
            logger.warn('Tried uncaching uncached node: {}'.format(node))

    def _get_cached_matches(self, node):
        q = self._get_query(node)
        concrete_model = node.model._meta.concrete_model
        model_cache = self._node_cache.get(concrete_model, {})
        matches = model_cache.get((q['attrs'], q['relations']), [])
        return [m for m in matches if m != node and issubclass(m.model, node.model) or issubclass(node.model, m.model)]

    def _instance_for_node(self, node):
        query = self._get_query(node)
        filter = {
            # TODO relations
            **query['attrs']
        }
        concrete_model = node.model._meta.concrete_model
        if concrete_model is not node.model:
            filter['type__in'] = self._matching_type_names(node)

        try:
            return concrete_model.get(**filter)
        except concrete_model.DoesNotExist:
            return None
        except concrete_model.MultipleObjectsReturned as ex:
            logger.warn('Multiple {}s returned for {}'.format(concrete_model, filter))
            raise ex

    def _matching_type_names(self, node):
        # list of all subclasses and superclasses of node.model
        format = lambda t: t if t.startswith('share.') else 'share.{}'.format(t)
        if node.model._meta.proxy:
            type_names = node.model.get_types() + [format(m._meta.model_name) for m in node.model.mro() if issubclass(m, node.model._meta.concrete_model) and m._meta.proxy]
        else:
            type_names = [format(node.model._meta.model_name)]
        return set(type_names)
