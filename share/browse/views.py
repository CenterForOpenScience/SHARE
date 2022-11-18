import rdflib
from django.db.models import F
from django.views.generic.base import TemplateView

from share import models as db
from share.util import rdfutil
from share.metadata_formats.turtle import RdfTurtleFormatter
from .serializers import FocusedContextBuilder


def _context_from_turtle(focus_pid, turtle_str):
    g = rdfutil.contextualized_graph()
    g.parse(format='turtle', data=turtle_str)
    return FocusedContextBuilder(g, focus_pid, 'turtle').build()


def _some_static_records():
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


def _some_normd_records():
    normd_qs = (
        db.NormalizedData.objects
        .filter(raw__suid__source_config__label='io.osf.registrations')
        .annotate(source_name=F('raw__suid__source_config__source__name'))
    )

    for normd in normd_qs[:20]:
        rdf_graph, focus_irl = RdfTurtleFormatter().build_rdf_graph(normd)
        yield FocusedContextBuilder(rdf_graph, focus_irl, normd.source_name).build()


class BrowseView(TemplateView):
    template_name = 'browse/browse.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_records'] = [
            *_some_normd_records(),
            # *_some_static_records(),
        ]
        return context


class BrowsePidView(TemplateView):
    template_name = 'browse/browse-pid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_record'] = [
        ]
        return context

    def _get_pid_record(self, maybe_pid):
        record = FormattedMetadataRecord.objects.get_record(
            suid=suid,
            record_format='rdf-turtle',
        )
        rdf_graph, focus_irl = RdfTurtleFormatter().build_rdf_graph()
        yield FocusedContextBuilder(rdf_graph, focus_irl, normd.source_name).build()
