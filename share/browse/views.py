import rdflib
from django.views.generic.base import TemplateView

from share.util import rdfutil


class FocusedContextBuilder:
    def __init__(self, rdf_graph, focus_id, ignored=None):
        assert isinstance(rdf_graph, rdflib.Graph)
        assert isinstance(focus_id, rdflib.term.Node)

        self._rdf_graph = rdf_graph
        self._ignored = set(ignored or ())
        self.focus_id = focus_id

    def build(self):
        assert isinstance(self.focus_id, rdflib.term.URIRef)
        return {
            'focus_pid': self.qname(self.focus_id),
            'focus_type_set': [
                self.qname(type_uri)
                for type_uri in self._rdf_graph.objects(self.focus_id, rdflib.RDF.type)
            ],
            'statement_set': self._statement_set(),
        }

    def qname(self, uri):
        return self._rdf_graph.qname(uri)

    def _follow_bnode_value(self, bnode_id):
        assert isinstance(bnode_id, rdflib.term.BNode)
        inner_builder = FocusedContextBuilder(
            rdf_graph=self._rdf_graph,
            focus_id=bnode_id,
            ignored=(self.focus_id, *self._ignored),
        )
        return {
            'is_nested': True,
            'nested_statement_set': inner_builder._statement_set(),
        }

    def _value(self, obj):
        if isinstance(obj, rdflib.term.Literal):
            return {
                'value': obj,
                'is_literal_str': isinstance(obj, rdflib.term.Literal),
            }
        if isinstance(obj, rdflib.term.BNode):
            return self._follow_bnode_value(obj)
        if isinstance(obj, rdflib.term.URIRef):
            obj_qname = self.qname(obj)
            is_short = (obj != obj_qname)
            return {
                'value': obj_qname,
                'is_short_uriref': is_short,
                'is_full_uriref': not is_short,
            }
        raise NotImplementedError(f'what is {obj} ({type(obj)}?)')

    def _statement(self, predicate_pid):
        statement_objects = set(self._rdf_graph.objects(
            subject=self.focus_id,
            predicate=predicate_pid,
        ))
        return (
            self.qname(predicate_pid),
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
            if not (isinstance(obj, rdflib.term.Node) and obj in self._ignored)
        )
        return [
            self._statement(predicate)
            for predicate in predicates
        ]


def _context_from_turtle(focus_pid, turtle_str):
    g = rdfutil.contextualized_graph()
    g.parse(format='turtle', data=turtle_str)
    return FocusedContextBuilder(g, focus_pid).build()


def _metadata_record_contexts():
    return [
        _context_from_turtle(
            rdflib.URIRef('https://foo.example/vocab/blamb'),
            '''
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix foo: <https://foo.example/vocab/> .

            foo:blamb a foo:Kebab ;
                dct:description "this is my description, much longer you see" ;
                foo:blarn foo:blorb ;
                foo:nested_pan
                    [
                        dct:description "this is a description of some nested stuff" ;
                        foo:blarn foo:blorb ;
                    ] ,
                    foo:blorb .
            ''',
        ),
        _context_from_turtle(
            rdflib.URIRef('https://osf.io/floom'),
            '''
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix osf: <https://osf.io/vocab/2022/> .
            @prefix osfio: <https://osf.io/> .
            @prefix foo: <https://foo.example/vocab/> .

            osfio:floom a osf:Project ;
                dct:title 'this is my title' ;
                dct:description 'this is my description, much longer you see' ;
                foo:blarn foo:blorb ;
                foo:nested_pan
                    [
                        dct:description 'this is a description of some nested stuff' ;
                        foo:blarn foo:blorb ;
                    ],
                    foo:blorb .
            ''',
        ),
        _context_from_turtle(
            rdflib.URIRef('https://osf.io/ppppp'),
            '''
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix osf: <https://osf.io/vocab/2022/> .
            @prefix osfio: <https://osf.io/> .
            @prefix foo: <https://foo.example/vocab/> .

            osfio:ppppp a osf:Preprint ;
                dct:title 'such a title' ;
                foo:keyword 'blop' ,
                            'bbloplop' ,
                            'bbbloploplop' ,
                            'bblopbbloploplop' ,
                            'bblopblopblopbloplop' ,
                            'bblopblopbloplop' ,
                            'bblopbloplop' ,
                            'bbloplop' ,
                            'bblopbloplop' ,
                            'bbloplop' ,
                            'bbloplop' ,
                            'bbloplop' ,
                            'bblopbloplop' ,
                            'bblopblopblopblopbloplop' ;
                foo:blarn foo:blorb .
            ''',
        ),
    ]


class BrowseView(TemplateView):
    template_name = 'browse/browse.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_records'] = _metadata_record_contexts()
        return context
