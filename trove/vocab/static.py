import functools
import pathlib

from primitive_metadata import primitive_rdf as rdf

from trove.util.iris import get_sufficiently_unique_iri
from .osfmap import OSFMAP_VOCAB
from .trove import TROVE_API_VOCAB


STATIC_THESAURUSES = (
    OSFMAP_VOCAB,
    TROVE_API_VOCAB,
)

STATIC_TURTLES = (
    'dublin_core_terms.turtle',
    'dcat.turtle',
    'owl.turtle',
    'rdf.turtle',
    'rdfs.turtle',
    'prov.turtle',
)


@functools.cache
def combined_thesaurus_with_suffuniq_subjects():
    return {
        get_sufficiently_unique_iri(_subj): _twoples
        for _subj, _twoples in _combined_thesaurus().items()
    }


def _combined_thesaurus():
    _combined_rdf = rdf.RdfGraph()
    for _thesaurus in STATIC_THESAURUSES:
        _combined_rdf.add_tripledict(_thesaurus)
    for _turtle_filename in STATIC_TURTLES:
        _combined_rdf.add_tripledict(_load_static_turtle(_turtle_filename))
    return _combined_rdf.tripledict


def _load_static_turtle(turtle_filename: str) -> rdf.RdfTripleDictionary:
    # assumed same directory as this file
    _turtle_filepath = pathlib.Path(__file__).parent / turtle_filename
    with open(_turtle_filepath) as _vocab_file:
        _turtle = _vocab_file.read()
    return rdf.tripledict_from_turtle(_turtle)
