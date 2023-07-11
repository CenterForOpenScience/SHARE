import dataclasses
import pathlib

import gather


RDF = gather.RDF  # http://www.w3.org/1999/02/22-rdf-syntax-ns#
RDFS = gather.RDFS  # http://www.w3.org/2000/01/rdf-schema#
OWL = gather.OWL  # http://www.w3.org/2002/07/owl#
DCTERMS = gather.IriNamespace('http://purl.org/dc/terms/')
FOAF = gather.IriNamespace('http://xmlns.com/foaf/0.1/')
DCAT = gather.IriNamespace('http://www.w3.org/ns/dcat#')
PROV = gather.IriNamespace('http://www.w3.org/ns/prov#')

# a new namespace for SHARE/trove concepts
TROVE = gather.IriNamespace('https://share.osf.io/vocab/2023/trove/')
# a wild namespace for whatever lingers from SHAREv2
SHAREv2 = gather.IriNamespace('https://share.osf.io/vocab/2017/sharev2/')


@dataclasses.dataclass(frozen=True)
class StaticVocab:
    iri_namespace: gather.IriNamespace
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
        iri_namespace=DCTERMS,
        shorthand_prefix='dcterms',
        turtle_filename='dublin_core_terms.turtle',
        turtle_focus_iri='http://purl.org/dc/terms/',
    ),
    StaticVocab(
        iri_namespace=DCAT,
        shorthand_prefix='dcat',
        turtle_filename='dcat.turtle',
        turtle_focus_iri='http://www.w3.org/ns/dcat',
    ),
    StaticVocab(
        iri_namespace=OWL,
        shorthand_prefix='owl',
        turtle_filename='owl.turtle',
        turtle_focus_iri='http://www.w3.org/2002/07/owl',
    ),
    StaticVocab(
        iri_namespace=RDF,
        shorthand_prefix='rdf',
        turtle_filename='rdf.turtle',
        turtle_focus_iri='http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    ),
    StaticVocab(
        iri_namespace=RDFS,
        shorthand_prefix='rdfs',
        turtle_filename='rdfs.turtle',
        turtle_focus_iri='http://www.w3.org/2000/01/rdf-schema#',
    ),
    StaticVocab(
        iri_namespace=PROV,
        shorthand_prefix='prov',
        turtle_filename='prov.turtle',
        turtle_focus_iri='http://www.w3.org/ns/prov#',
    ),
))
