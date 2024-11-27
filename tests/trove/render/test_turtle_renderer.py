from primitive_metadata import primitive_rdf as rdf

from trove.render.turtle import RdfTurtleRenderer
from trove.render._rendering import SimpleRendering
from . import _base


class _BaseTurtleRendererTest(_base.TroveRendererTests):
    renderer_class = RdfTurtleRenderer

    def _get_rendered_output(self, rendering):
        return rdf.tripledict_from_turtle(super()._get_rendered_output(rendering))


class TestTurtleRenderer(_BaseTurtleRendererTest):
    expected_outputs = {
        'simple_card': SimpleRendering(
            mediatype='text/turtle',
            rendered_content='''
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix trove: <https://share.osf.io/vocab/2023/trove/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://blarg.example/vocab/aCard> a dcat:CatalogRecord, trove:Indexcard ;
    dcterms:issued "2024-01-01"^^xsd:date ;
    dcterms:modified "2024-01-01"^^xsd:date ;
    foaf:primaryTopic <http://blarg.example/vocab/anItem> ;
    trove:focusIdentifier "http://blarg.example/vocab/anItem"^^rdf:string ;
    trove:resourceMetadata "{\\"@id\\": \\"http://blarg.example/vocab/anItem\\", \\"title\\": \\"an item, yes\\"}"^^rdf:JSON .
''',
        ),
    }


class TestTurtleTrovesearchRenderer(_BaseTurtleRendererTest, _base.TrovesearchRendererTests):
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='text/turtle',
            rendered_content='''
@prefix trove: <https://share.osf.io/vocab/2023/trove/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://blarg.example/vocab/aSearch> a trove:Cardsearch ;
    trove:totalResultCount 0 .
''',
        ),
        'few_results': SimpleRendering(
            mediatype='text/turtle',
            rendered_content='''
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix trove: <https://share.osf.io/vocab/2023/trove/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://blarg.example/vocab/aSearchFew> a trove:Cardsearch ;
    trove:searchResultPage [
        a rdf:Seq ;
        rdf:_1 [
            a trove:SearchResult ;
            trove:indexCard <http://blarg.example/vocab/aCard>
        ] ;
        rdf:_2 [
            a trove:SearchResult ;
            trove:indexCard <http://blarg.example/vocab/aCardd>
        ] ;
        rdf:_3 [
            a trove:SearchResult ;
            trove:indexCard <http://blarg.example/vocab/aCarddd>
        ]
    ] ;
    trove:totalResultCount 3 .

<http://blarg.example/vocab/aCard> a dcat:CatalogRecord, trove:Indexcard ;
    dcterms:issued "2024-01-01"^^xsd:date ;
    dcterms:modified "2024-01-01"^^xsd:date ;
    foaf:primaryTopic <http://blarg.example/vocab/anItem> ;
    trove:focusIdentifier "http://blarg.example/vocab/anItem"^^rdf:string ;
    trove:resourceMetadata "{\\"@id\\": \\"http://blarg.example/vocab/anItem\\", \\"title\\": \\"an item, yes\\"}"^^rdf:JSON .

<http://blarg.example/vocab/aCardd> a dcat:CatalogRecord, trove:Indexcard ;
    dcterms:issued "2024-02-02"^^xsd:date ;
    dcterms:modified "2024-02-02"^^xsd:date ;
    foaf:primaryTopic <http://blarg.example/vocab/anItemm> ;
    trove:focusIdentifier "http://blarg.example/vocab/anItemm"^^rdf:string ;
    trove:resourceMetadata "{\\"@id\\": \\"http://blarg.example/vocab/anItemm\\", \\"title\\": \\"an itemm, yes\\"}"^^rdf:JSON .

<http://blarg.example/vocab/aCarddd> a dcat:CatalogRecord, trove:Indexcard ;
    dcterms:issued "2024-03-03"^^xsd:date ;
    dcterms:modified "2024-03-03"^^xsd:date ;
    foaf:primaryTopic <http://blarg.example/vocab/anItemmm> ;
    trove:focusIdentifier "http://blarg.example/vocab/anItemmm"^^rdf:string ;
    trove:resourceMetadata "{\\"@id\\": \\"http://blarg.example/vocab/anItemmm\\", \\"title\\": \\"an itemmm, yes\\"}"^^rdf:JSON .
''',
        ),
    }
