import logging
import pendulum

from django.db.models import Q, DateTimeField

from share.exceptions import MergeRequired
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
        # Sort by type and id as well to get consitent sorting
        nodes = sorted(change_graph.nodes, key=lambda x: (self._disambiguweight(x), x.type, x.id), reverse=True)

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
                    # if instance and isinstance(instance, list):
                    #     same_type = [i for i in instance if isinstance(i, n.model)]
                    #     if not same_type:
                    #         logger.error('Found multiple matches for %s, and none were of type %s: %s', n, n.model, instance)
                    #         raise NotImplementedError('Multiple matches found', n, instance)
                    #     elif len(same_type) > 1:
                    #         logger.error('Found multiple matches of type %s for %s: %s', n.model, n, same_type)
                    #         raise NotImplementedError('Multiple matches found', n, same_type)
                    #     logger.warning('Found multiple matches for %s, but only one of type %s, fortunately.', n, n.model)
                    #     instance = same_type.pop()
                    if instance:
                        changed = True
                        n.instance = instance
                        logger.debug('Disambiguated %s to %s', n, instance)

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
        concrete_model = node.model._meta.concrete_model

        if concrete_model.__name__ == 'Subject':
            return self._instance_for_subject(node)

        info = self._index.get_info(node)
        if not info.all and not info.any:
            return None

        all_query = Q()
        for k, v in info.all:
            k, v = self._query_pair(k, v)
            if k and v:
                all_query &= Q(**{k: v})
            else:
                return None

        queries = []
        for k, v in info.any:
            k, v = self._query_pair(k, v)
            if k and v:
                queries.append(all_query & Q(**{k: v}))

        if (info.all and not all_query.children) or (info.any and not queries):
            return None

        if info.matching_types:
            all_query &= Q(type__in=info.matching_types)

        constrain = [Q()]
        if hasattr(node.model, '_typedmodels_type'):
            constrain.append(Q(type__in=node.model.get_types()))
            constrain.append(Q(type=node.model._typedmodels_type))

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

        logger.error('Could not disambiguate %s. Too many results found from %s %s', node.model, all_query, queries)
        raise MergeRequired('Multiple {0}s found'.format(node.model), node.model, queries)

    def _instance_for_subject(self, node):
        # Subject disambiguation is a bit weird: Match taxonomy AND (uri OR name)
        qs = None
        if node.related('central_synonym') is None:
            # Central taxonomy
            qs = node.model.objects.filter(central_synonym__isnull=True)
        else:
            # Custom taxonomy
            source = node.graph.source
            if source:
                qs = node.model.objects.filter(taxonomy__source=source)

        if not qs:
            return None

        uri = node.attrs.get('uri')
        if uri:
            try:
                return qs.get(uri=uri)
            except node.model.DoesNotExist:
                pass

        name = node.attrs.get('name')
        if name:
            try:
                return qs.get(name=name)
            except node.model.DoesNotExist:
                pass
        logger.debug('Could not disambiguate subject %s', node)
        return None

    def _query_pair(self, key, value):
        try:
            if not value.instance:
                return (None, None)
            return ('{}__id'.format(key), value.instance.id)
        except AttributeError:
            return (key, value)

    def _merge_nodes(self, source, replacement):
        assert source.graph is replacement.graph
        for k, v in source.attrs.items():
            if k in replacement.attrs:
                old_val = replacement.attrs[k]
                if v == old_val:
                    continue
                field = replacement.model._meta.get_field(k)
                if isinstance(field, DateTimeField):
                    new_val = max(pendulum.parse(v), pendulum.parse(old_val)).isoformat()
                else:
                    # use the longer value, or the first alphabetically if they're the same length
                    new_val = sorted([v, old_val], key=lambda x: (-len(str(x)), x))[0]
            else:
                new_val = source.attrs[k]
            replacement.attrs[k] = new_val

        from share.models import Person
        if replacement.model == Person:
            replacement.attrs['name'] = ''
            Person.normalize(replacement, replacement.graph)

        source.graph.replace(source, replacement)

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
                if info.matching_types:
                    return [m for m in matches if m != node and m.model._meta.label_lower in info.matching_types]
                else:
                    return [m for m in matches if m != node]
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
                try:
                    constrain_types = self._node.model.Disambiguation.constrain_types
                except AttributeError:
                    constrain_types = False
                if not constrain_types:
                    return None

                # list of all subclasses and superclasses of node.model that could be the type of a node
                concrete_model = self._node.model._meta.concrete_model
                if concrete_model is self._node.model:
                    type_names = [self._node.model._meta.label_lower]
                else:
                    subclasses = self._node.model.get_types()
                    superclasses = [m._meta.label_lower for m in self._node.model.__mro__ if issubclass(m, concrete_model) and m._meta.proxy]
                    type_names = subclasses + superclasses
                return set(type_names)

            def _field_values(self, field_name):
                field = self._node.model._meta.get_field(field_name)
                if field.is_relation:
                    if field.one_to_many:
                        for edge in self._node.related(name=field_name, forward=False):
                            yield edge.subject
                    elif field.many_to_one:
                        edge = self._node.related(name=field_name, backward=False)
                        yield None if edge is None else edge.related
                    elif field.many_to_many:
                        # TODO?
                        raise NotImplementedError()
                else:
                    if field_name in self._node.attrs:
                        value = self._node.attrs[field.name]
                        if value != '':
                            yield value
