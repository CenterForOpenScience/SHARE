import logging
import pendulum

from django.db.models import Q, DateTimeField

from share.exceptions import MergeRequired

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
