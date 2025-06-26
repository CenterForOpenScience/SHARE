from collections.abc import Generator
from typing import Any

from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove.util.iris import get_sufficiently_unique_iri
from trove.vocab import namespaces as ns
from trove.vocab import static_vocab
from trove.vocab.trove import TROVE_API_THESAURUS


type GathererGenerator = Generator[rdf.RdfTriple | rdf.RdfTwople]


TROVEBROWSE_NORMS = gather.GatheringNorms.new(
    namestory=(
        rdf.literal('trovebrowse', language='en'),
        rdf.literal('browse a trove of IRI-linked metadata', language='en'),
    ),
    focustype_iris={},
    param_iris={ns.TROVE.blendCards},
    thesaurus=TROVE_API_THESAURUS,

)


trovebrowse = gather.GatheringOrganizer(
    namestory=(
        rdf.literal('trovebrowse organizer', language='en'),
    ),
    norms=TROVEBROWSE_NORMS,
    gatherer_params={'blend_cards': ns.TROVE.blendCards},
)


@trovebrowse.gatherer(ns.FOAF.isPrimaryTopicOf)
def gather_cards_focused_on(focus: gather.Focus, *, blend_cards: bool) -> GathererGenerator:
    _identifier_qs = trove_db.ResourceIdentifier.objects.queryset_for_iris(focus.iris)
    _indexcard_qs = trove_db.Indexcard.objects.filter(focus_identifier_set__in=_identifier_qs)
    if blend_cards:
        for _latest_resource_description in trove_db.LatestResourceDescription.objects.filter(indexcard__in=_indexcard_qs):
            yield from rdf.iter_tripleset(_latest_resource_description.as_rdf_tripledict())
    else:
        for _indexcard in _indexcard_qs:
            _card_iri = _indexcard.get_iri()
            yield (ns.FOAF.isPrimaryTopicOf, _card_iri)
            yield (_card_iri, ns.RDF.type, ns.TROVE.Indexcard)


@trovebrowse.gatherer(ns.TROVE.thesaurusEntry)
def gather_thesaurus_entry(focus: gather.Focus, *, blend_cards: bool) -> GathererGenerator:
    _thesaurus = static_vocab.combined_thesaurus__suffuniq()
    for _iri in focus.iris:
        _suffuniq_iri = get_sufficiently_unique_iri(_iri)
        _thesaurus_entry = _thesaurus.get(_suffuniq_iri, None)
        if _thesaurus_entry:
            if blend_cards:
                yield from rdf.iter_twoples(_thesaurus_entry)
            else:
                yield (ns.TROVE.thesaurusEntry, rdf.QuotedGraph({_iri: _thesaurus_entry}, focus_iri=_iri))


@trovebrowse.gatherer(ns.TROVE.usedAtPath)
def gather_paths_used_at(focus: gather.Focus, **kwargs: Any) -> GathererGenerator:
    yield from ()  # TODO via elasticsearch aggregation
