from __future__ import annotations
import base64
from collections import defaultdict
import contextlib
import dataclasses
import datetime
import functools
import json
import logging
import typing

from django.db.models import Exists, OuterRef
from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove.trovesearch.search_params import (
    is_globpath,
)
from trove.util.iris import get_sufficiently_unique_iri, is_worthwhile_iri
from trove.vocab.namespaces import (
    DCTERMS,
    FOAF,
    OSFMAP,
    OWL,
    RDF,
    RDFS,
    SKOS,
    TROVE,
    XSD,
)
from trove.vocab.osfmap import is_date_property


_logger = logging.getLogger(__name__)


###
# type aliases

Propertypath = tuple[str, ...]


###
# constants

SKIPPABLE_PROPERTIES = (
    OSFMAP.contains,  # too much, not helpful
    OWL.sameAs,  # handled special
)

TITLE_PROPERTIES = (DCTERMS.title,)
NAME_PROPERTIES = (FOAF.name, OSFMAP.fileName)
LABEL_PROPERTIES = (RDFS.label, SKOS.prefLabel, SKOS.altLabel)
NAMELIKE_PROPERTIES = (*TITLE_PROPERTIES, *NAME_PROPERTIES, *LABEL_PROPERTIES)

VALUESEARCH_MAX = 234
CARDSEARCH_MAX = 9997

KEYWORD_LENGTH_MAX = 8191  # skip keyword terms that might exceed lucene's internal limit
# (see https://www.elastic.co/guide/en/elasticsearch/reference/current/ignore-above.html)
KEYWORD_MAPPING = {'type': 'keyword', 'ignore_above': KEYWORD_LENGTH_MAX}
FLATTENED_MAPPING = {'type': 'flattened', 'ignore_above': KEYWORD_LENGTH_MAX}
TEXT_MAPPING = {
    'type': 'text',
    'index_options': 'offsets',  # for highlighting
}
IRI_KEYWORD_MAPPING = {
    'type': 'object',
    'properties': {  # for indexing iri values two ways:
        'exact': KEYWORD_MAPPING,  # the exact iri value (e.g. "https://foo.example/bar/")
        'suffuniq': KEYWORD_MAPPING,  # "sufficiently unique" (e.g. "://foo.example/bar")
    },
}


###
# utilities

def latest_rdf_for_indexcard_pks(indexcard_pks):
    return (
        trove_db.LatestIndexcardRdf.objects
        .filter(indexcard_id__in=indexcard_pks)
        .filter(Exists(
            trove_db.DerivedIndexcard.objects
            .filter(upriver_indexcard_id=OuterRef('indexcard_id'))
            .filter(deriver_identifier__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iri(TROVE['derive/osfmap_json'])
            ))
        ))
        .exclude(indexcard__deleted__isnull=False)
        .select_related('indexcard__source_record_suid__source_config')
        .prefetch_related('indexcard__focus_identifier_set')
    )


def iri_synonyms(iri: str, rdfdoc: rdf.RdfGraph) -> set[str]:
    # note: extremely limited inference -- assumes objects of owl:sameAs are not used as subjects
    _synonyms = (
        _synonym
        for _synonym in rdfdoc.q(iri, OWL.sameAs)
        if is_worthwhile_iri(_synonym)
    )
    return {iri, *_synonyms}


def iris_synonyms(iris: typing.Iterable[str], rdfdoc: rdf.RdfGraph) -> set[str]:
    return {
        _synonym
        for _iri in iris
        for _synonym in iri_synonyms(_iri, rdfdoc)
    }


def propertypath_as_keyword(path: Propertypath) -> str:
    assert not is_globpath(path)
    return json.dumps([
        get_sufficiently_unique_iri(_iri)
        for _iri in path
    ])


def propertypath_as_field_name(path: Propertypath) -> str:
    return b64(propertypath_as_keyword(path))


def b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def b64_reverse(b64_str: str) -> str:
    return base64.urlsafe_b64decode(b64_str.encode()).decode()


def suffuniq_iris(iris: typing.Iterable[str]) -> list[str]:
    # deduplicates, may reorder
    return list({
        get_sufficiently_unique_iri(_iri)
        for _iri in iris
    })


def _dict_of_sets():
    return defaultdict(set)


@dataclasses.dataclass
class GraphWalk:
    rdfdoc: rdf.RdfGraph
    focus_iri: str
    already_visiting: set[str] = dataclasses.field(default_factory=set)
    iri_values: dict[Propertypath, set[str]] = dataclasses.field(
        default_factory=_dict_of_sets,
    )
    text_values: dict[Propertypath, set[rdf.Literal]] = dataclasses.field(
        default_factory=_dict_of_sets,
    )
    date_values: dict[Propertypath, set[datetime.date]] = dataclasses.field(
        default_factory=_dict_of_sets,
    )
    integer_values: dict[Propertypath, set[int]] = dataclasses.field(
        default_factory=_dict_of_sets,
    )
    paths_walked: set[Propertypath] = dataclasses.field(default_factory=set)

    def __post_init__(self):
        for _walk_path, _walk_obj in self._walk_from_subject(self.focus_iri):
            self.paths_walked.add(_walk_path)
            if isinstance(_walk_obj, str):
                self.iri_values[_walk_path].add(_walk_obj)
            elif isinstance(_walk_obj, datetime.date):
                self.date_values[_walk_path].add(_walk_obj)
            elif is_date_property(_walk_path[-1]):
                try:
                    _parsed_date = datetime.date.fromisoformat(_walk_obj.unicode_value)
                except ValueError:
                    _logger.debug('skipping malformatted date "%s"', _walk_obj.unicode_value)
                else:
                    self.date_values[_walk_path].add(_parsed_date)
            elif isinstance(_walk_obj, rdf.Literal):
                if XSD.integer in _walk_obj.datatype_iris:
                    self.integer_values[_walk_path].add(_walk_obj)
                if {RDF.string, RDF.langString}.intersection(_walk_obj.datatype_iris):
                    self.text_values[_walk_path].add(_walk_obj.unicode_value)

    def shortwalk_from(self, from_iri: str) -> GraphWalk:
        return GraphWalk(
            self.rdfdoc,
            from_iri,
            already_visiting={self.focus_iri},
        )

    def _walk_from_subject(
        self,
        iri: str,
        path_so_far: tuple[str, ...] = (),
    ) -> typing.Iterator[tuple[Propertypath, rdf.RdfObject]]:
        '''walk the graph from the given subject, yielding (pathkey, obj) for every reachable object
        '''
        if iri in self.already_visiting:
            return
        with self._visit(iri):
            _twoples = self.rdfdoc.tripledict.get(iri, {})
            for _next_steps, _obj in walk_twoples(_twoples):
                _path = (*path_so_far, *_next_steps)
                yield (_path, _obj)
                if isinstance(_obj, str):  # step further for iri
                    yield from self._walk_from_subject(_obj, path_so_far=_path)

    @functools.cached_property
    def paths_by_iri(self) -> defaultdict[str, set[Propertypath]]:
        _paths_by_iri: defaultdict[str, set[Propertypath]] = defaultdict(set)
        for _path, _iris in self.iri_values.items():
            for _iri in _iris:
                _paths_by_iri[_iri].add(_path)
        return _paths_by_iri

    @contextlib.contextmanager
    def _visit(self, focus_obj):
        assert focus_obj not in self.already_visiting
        self.already_visiting.add(focus_obj)
        yield
        self.already_visiting.discard(focus_obj)


def walk_twoples(
    twoples: rdf.RdfTwopleDictionary | rdf.Blanknode,
) -> typing.Iterator[tuple[Propertypath, rdf.RdfObject]]:
    if isinstance(twoples, frozenset):
        _iter_twoples = (
            (_pred, _obj)
            for _pred, _obj in twoples
            if _pred not in SKIPPABLE_PROPERTIES
        )
    else:
        _iter_twoples = (
            (_pred, _obj)
            for _pred, _obj_set in twoples.items()
            if _pred not in SKIPPABLE_PROPERTIES
            for _obj in _obj_set
        )
    for _pred, _obj in _iter_twoples:
        _path = (_pred,)
        if isinstance(_obj, frozenset):
            for _innerpath, _innerobj in walk_twoples(_obj):
                _fullpath = (*_path, *_innerpath)
                yield (_fullpath, _innerobj)
        else:
            yield (_path, _obj)
