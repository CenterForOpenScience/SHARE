import rdflib


class FocusedContextBuilder:
    def __init__(self, rdf_graph, focus_id, source_name, ignored_set=None):
        assert isinstance(rdf_graph, rdflib.Graph)
        assert isinstance(focus_id, rdflib.term.Node)

        self._rdf_graph = rdf_graph
        self._ignored_set = ignored_set or set()
        self._source_name = source_name
        self.focus_id = focus_id

    def build(self):
        statement_set = self._statement_set()
        return {
            'focus_pid': self.shortname(self.focus_id),
            'focus_type_set': [
                self.display_uri(type_uri)
                for type_uri in self._rdf_graph.objects(self.focus_id, rdflib.RDF.type)
            ],
            'statement_set': statement_set,
            'record_source': self._source_name,
            'referenced_pids': self._gather_references(statement_set),
        }

    def display_uri(self, uri):
        return self._rdf_graph.namespace_manager.normalizeUri(uri)

    def _nested_statement_set(self, node_id):
        assert isinstance(node_id, rdflib.term.Node)
        inner_builder = FocusedContextBuilder(
            rdf_graph=self._rdf_graph,
            focus_id=node_id,
            source_name=self._source_name,
            ignored_set=self._ignored_set,
        )
        return inner_builder._statement_set()

    def _value(self, obj):
        if isinstance(obj, rdflib.term.Literal):
            return {
                'literal_value': obj,
            }
        if isinstance(obj, rdflib.term.BNode):
            return {
                'nested_statement_set': self._nested_statement_set(obj),
            }
        if isinstance(obj, rdflib.term.URIRef):
            return {
                'display_uri': self.display_uri(obj),
                'full_uri': obj,
                'nested_statement_set': self._nested_statement_set(obj),
            }
        raise NotImplementedError(f'what is {obj} ({type(obj)}?)')

    def _statement(self, predicate_pid):
        statement_objects = set(self._rdf_graph.objects(
            subject=self.focus_id,
            predicate=predicate_pid,
        ))
        return (
            self.shortname(predicate_pid),
            [
                self._value(obj)
                for obj in statement_objects
            ],
        )

    def _statement_set(self):
        predicate_objects = self._rdf_graph.predicate_objects(
            subject=self.focus_id,
        )
        predicates = set(
            predicate_uri
            for predicate_uri, obj in predicate_objects
            if obj not in self._ignored_set
        )
        if predicates:
            self._ignored_set.add(self.focus_id)
        return [
            self._statement(predicate)
            for predicate in predicates
        ]

    def _gather_references(self, statement_set):
        return []  # TODO
