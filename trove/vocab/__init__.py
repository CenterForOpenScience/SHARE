import dataclasses
import pathlib

from gather import primitive_rdf

from . import namespaces


@dataclasses.dataclass(frozen=True)
class StaticVocab:
    iri_namespace: primitive_rdf.IriNamespace
    shorthand_prefix: str  # for convenience within this system
    turtle_filename: str  # assumed same directory as this file
    turtle_focus_iri: str  # may be different from IriNamespace

    def turtle_filepath(self):
        return pathlib.Path(__file__).parent / self.turtle_filename

    def turtle(self):
        with open(self.turtle_filepath()) as _vocab_file:
            return _vocab_file.read()


VOCAB_SET = frozenset((
    StaticVocab(
        iri_namespace=namespaces.DCTERMS,
        shorthand_prefix='dcterms',
        turtle_filename='dublin_core_terms.turtle',
        turtle_focus_iri='http://purl.org/dc/terms/',
    ),
    StaticVocab(
        iri_namespace=namespaces.DCAT,
        shorthand_prefix='dcat',
        turtle_filename='dcat.turtle',
        turtle_focus_iri='http://www.w3.org/ns/dcat',
    ),
    StaticVocab(
        iri_namespace=namespaces.OWL,
        shorthand_prefix='owl',
        turtle_filename='owl.turtle',
        turtle_focus_iri='http://www.w3.org/2002/07/owl',
    ),
    StaticVocab(
        iri_namespace=namespaces.RDF,
        shorthand_prefix='rdf',
        turtle_filename='rdf.turtle',
        turtle_focus_iri='http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    ),
    StaticVocab(
        iri_namespace=namespaces.RDFS,
        shorthand_prefix='rdfs',
        turtle_filename='rdfs.turtle',
        turtle_focus_iri='http://www.w3.org/2000/01/rdf-schema#',
    ),
    StaticVocab(
        iri_namespace=namespaces.PROV,
        shorthand_prefix='prov',
        turtle_filename='prov.turtle',
        turtle_focus_iri='http://www.w3.org/ns/prov#',
    ),
    # TODO: osfmap, trove (load from tripledict)
))
