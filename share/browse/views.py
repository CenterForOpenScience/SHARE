import random

import rdflib
from django.db.models import F
from django.views.generic.base import TemplateView

from share import models as db
from share.util import rdfutil
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
        rdfgraph = normd.get_rdfgraph()
        yield FocusedContextBuilder(
            rdfgraph,
            normd.described_resource_uri,
            normd.source_name,
        ).build()


class BrowseView(TemplateView):
    template_name = 'browse/browse.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_records'] = [
            *_some_normd_records(),
            # *_some_static_records(),
        ]
        context['random_seed'] = random.random()
        return context


class BrowsePidView(TemplateView):
    template_name = 'browse/browse.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_records'] = list(self._get_pid_records(kwargs['pid']))

    def _get_pid_records(self, maybe_pid):
        pid_uri = rdfutil.normalize_pid_uri(maybe_pid)
        records = db.FormattedMetadataRecord.objects.get_by_pid(
            pid_uri,
            record_format='turtle',
        )
        for record in records:
            rdf_graph = rdfutil.contextualized_graph().parse(
                data=record.formatted_metadata,
                format='turtle',
            )
            yield FocusedContextBuilder(
                rdf_graph,
                pid_uri,
                record.suid.source_config.source.long_title,
            ).build()
