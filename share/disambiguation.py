import logging
import pendulum

from django.db.models import Q, DateTimeField

from share.util import DictHashingDict

__all__ = ('GraphDisambiguator', )

logger = logging.getLogger(__name__)


class GraphDisambiguator:
    def __init__(self):
        self._index = self.NodeIndex()

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
            # TODO update affected nodes after changes instead of rebuilding the index every loop
            self._index.clear()

            for n in tuple(nodes):
                if n.is_merge or (find_instances and n.instance):
                    continue
                matches = self._index.get_matches(n)
                if len(matches) > 1:
                    # TODO?
                    raise NotImplementedError('Multiple matches that apparently didn\'t match each other?\nNode: {}\nMatches: {}'.format(n, matches))

                if matches:
                    # remove duplicates within the graph
                    match = matches.pop()
                    if n.model != match.model and issubclass(n.model, match.model):
                        # remove the node with the less-specific class
                        logger.debug('Found duplicate! Keeping {}, pruning {}'.format(n, match))
                        self._index.remove(match)
                        nodes.remove(match)
                        self._merge_nodes(match, n)
                        self._index.add(n)
                    else:
                        logger.debug('Found duplicate! Keeping {}, pruning {}'.format(match, n))
                        nodes.remove(n)
                        self._merge_nodes(n, match)
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

                self._index.add(n)

    def _disambiguweight(self, node):
        # Models with exactly 1 foreign key field (excluding those added by
        # ShareObjectMeta) are disambiguated first, because they might be used
        # to uniquely identify the object they point to. Then do the models with
        # 0 FKs, then 2, 3, etc.
        ignored = {'same_as', 'extra'}
        fk_count = sum(1 for f in node.model._meta.get_fields() if f.editable and (f.many_to_one or f.one_to_one) and f.name not in ignored)
        return fk_count if fk_count == 1 else -fk_count

    def _instance_for_node(self, node):
        info = self._index.get_info(node)
        concrete_model = node.model._meta.concrete_model

        query_pairs = []
        for k, v in info.all:
            k, v = self._query_pair(k, v)
            if k is not None and v is not None:
                query_pairs.append((k, v))
            else:
                return None
        if concrete_model is not node.model:
            query_pairs.append(('type__in', info.matching_types))
        query = Q(**dict(query_pairs))

        any_query = None
        for k, v in info.any:
            k, v = self._query_pair(k, v)
            if k is not None and v is not None:
                q = Q(**{k: v})
                any_query = any_query | q if any_query else q
        if info.any and not any_query:
            return None
        if any_query:
            query &= any_query

        found = set(concrete_model.objects.filter(query))
        if len(found) == 1:
            return found.pop()
        logger.warn('Multiple {}s returned for {}'.format(concrete_model, filter))
        return list(found)

    def _query_pair(self, key, value):
        try:
            if not value.instance:
                return (None, None)
            return ('{}__id'.format(key), value.instance.id)
        except AttributeError:
            return (key, value)

    def _merge_nodes(self, source, replacement):
        from share.models import Person
        if isinstance(replacement, Person):
            self._merge_person_attrs(source, replacement)
        else:
            self._merge_attrs(source, replacement, source.attrs.keys())
        source.graph.replace(source, replacement)

    def _merge_person_attrs(self, source, replacement):
        from share.models import Person
        keys = source.attrs.keys()
        try:
            keys.remove('name')
        except ValueError:
            pass
        self._merge_attrs(source, replacement, keys)
        Person.normalize(replacement, replacement.graph)

    def _merge_attrs(self, source, replacement, keys):
        for k in keys:
            if k not in source.attrs:
                continue
            v = source.attrs[k]
            if k in replacement.attrs:
                old_val = replacement.attrs[k]
                if v == old_val:
                    continue
                field = replacement.model._meta.get_field(k)
                if isinstance(field, DateTimeField):
                    new_val = max(pendulum.parse(v), pendulum.parse(old_val)).isoformat()
                else:
                    # use the longer value, or the first alphabetically if they're the same length
                    new_val = sorted([v, old_val], key=lambda x: (-len(x), x))[0]
            else:
                new_val = source.attrs[k]
            replacement.attrs[k] = new_val

    class NodeIndex:
        def __init__(self):
            self._index = {}
            self._info_cache = {}

        def clear(self):
            self._index.clear()
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
            by_model = self._index.setdefault(node.model._meta.concrete_model, DictHashingDict())
            if info.any:
                all_cache = by_model.setdefault(info.all, DictHashingDict())
                for item in info.any:
                    all_cache.setdefault(item, []).append(node)
            elif info.all:
                by_model.setdefault(info.all, []).append(node)
            else:
                logger.debug('Nothing to disambiguate on. Ignoring node {}'.format(node))

        def remove(self, node):
            info = self.get_info(node)
            try:
                all_cache = self._index[node.model._meta.concrete_model][info.all]
                if info.any:
                    for item in info.any:
                        all_cache[item].remove(node)
                else:
                    all_cache.remove(node)
            except (KeyError, ValueError) as ex:
                raise ValueError('Could not remove node from cache: Node {} not found!'.format(node)) from ex

        def get_matches(self, node):
            info = self.get_info(node)
            matches = set()
            try:
                matches_all = self._index[node.model._meta.concrete_model][info.all]
                if info.any:
                    for item in info.any:
                        matches.update(matches_all.get(item, []))
                elif info.all:
                    matches.update(matches_all)
                # TODO use `info.tie_breaker` when there are multiple matches
                return [m for m in matches if m != node and 'share.{}'.format(m.model._meta.model_name) in info.matching_types]
            except KeyError:
                return []

        # TODO better name
        class NodeInfo:
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
                assert len(values) == len(all)
                return values

            def _any(self):
                try:
                    any = self._node.model.Disambiguation.any
                except AttributeError:
                    return ()
                return tuple((f, v) for f in any for v in self._field_values(f))

            def _matching_types(self):
                # list of all subclasses and superclasses of node.model that could be the type of a node
                def fmt(model):
                    return 'share.{}'.format(model._meta.model_name)
                concrete_model = self._node.model._meta.concrete_model
                if concrete_model is self._node.model:
                    type_names = [fmt(self._node.model)]
                else:
                    subclasses = self._node.model.get_types()
                    superclasses = [fmt(m) for m in self._node.model.__mro__ if issubclass(m, concrete_model) and m._meta.proxy]
                    type_names = subclasses + superclasses
                return set(type_names)

            def _field_values(self, field_name):
                field = self._node.model._meta.get_field(field_name)
                if field.is_relation:
                    if field.one_to_many:
                        for edge in self._node.related(name=field_name, forward=False):
                            yield edge.subject
                    elif field.many_to_one:
                        yield self._node.related(name=field_name, backward=False).related
                    elif field.many_to_many:
                        # TODO?
                        raise NotImplementedError()
                else:
                    if field_name in self._node.attrs:
                        value = self._node.attrs[field.name]
                        if value != '':
                            yield value
