import functools
import pathlib
import types
from primitive_metadata import primitive_rdf as rdf
import rdflib

from trove.util.iris import get_sufficiently_unique_iri
from trove.vocab.osfmap import OSFMAP_THESAURUS
from trove.vocab.trove import TROVE_API_THESAURUS


__all__ = (
    'combined_thesaurus',
    'combined_thesaurus__suffuniq',
)


_STATIC_THESAURUSES = (
    OSFMAP_THESAURUS,
    TROVE_API_THESAURUS,
)

_STATIC_TURTLES = (
    'dublin_core_abstract_model.turtle',
    'dublin_core_elements.turtle',
    'dublin_core_terms.turtle',
    'dublin_core_type.turtle',
    'dcat.turtle',
    'owl.turtle',
    'rdf.turtle',
    'rdfs.turtle',
    'prov.turtle',
)

_STATIC_XMLS = (
    'skos.rdf.xml',
    'foaf.rdf.xml',
)


@functools.cache
def combined_thesaurus():  # type: ignore
    _combined_rdf = rdf.RdfGraph()
    for _thesaurus in _STATIC_THESAURUSES:
        _combined_rdf.add_tripledict(_thesaurus)
    for _turtle_filename in _STATIC_TURTLES:
        _combined_rdf.add_tripledict(_load_static_turtle(_turtle_filename))
    for _xml_filename in _STATIC_XMLS:
        _combined_rdf.add_tripledict(_load_static_xml(_xml_filename))
    return types.MappingProxyType(_combined_rdf.tripledict)


@functools.cache
def combined_thesaurus__suffuniq():  # type: ignore
    return types.MappingProxyType({
        get_sufficiently_unique_iri(_subj): _twoples
        for _subj, _twoples in combined_thesaurus().items()
    })


def _load_static_turtle(turtle_filename: str) -> rdf.RdfTripleDictionary:
    # assumed same directory as this file
    with open(_local_filepath(turtle_filename)) as _vocab_file:
        _turtle = _vocab_file.read()
    return rdf.tripledict_from_turtle(_turtle)


def _load_static_xml(xml_filename: str) -> rdf.RdfTripleDictionary:
    # assumed same directory as this file
    _graph = rdflib.Graph()
    with open(_local_filepath(xml_filename)) as _vocab_file:
        _graph.parse(_vocab_file, format='xml')
    return rdf.tripledict_from_rdflib(_graph)


def _local_filepath(filename: str) -> pathlib.Path:
    # assumed same directory as this file
    return pathlib.Path(__file__).parent / filename
