from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove.util.iris import get_sufficiently_unique_iri
from trove.vocab import namespaces as ns
from trove.vocab import static_vocab
from trove.vocab.trove import (
    TROVE_API_THESAURUS,
)


TROVEBROWSE_NORMS = gather.GatheringNorms.new(
    namestory=(
        rdf.literal('trovebrowse', language='en'),
        rdf.literal('browse a trove of IRI-linked metadata', language='en'),
    ),
    focustype_iris={},
    param_iris={ns.TROVE.withAmalgamation},
    thesaurus=TROVE_API_THESAURUS,

)


trovebrowse = gather.GatheringOrganizer(
    namestory=(
        rdf.literal('trovebrowse organizer', language='en'),
    ),
    norms=TROVEBROWSE_NORMS,
    gatherer_params={'with_amalgamation': ns.TROVE.withAmalgamation},
)


@trovebrowse.gatherer()
def gather_thesaurus_entry(focus, *, with_amalgamation: bool):
    _thesaurus = static_vocab.combined_thesaurus__suffuniq()
    for _iri in focus.iris:
        _suffuniq_iri = get_sufficiently_unique_iri(_iri)
        _thesaurus_entry = _thesaurus.get(_suffuniq_iri, None)
        if _thesaurus_entry:
            if with_amalgamation:
                yield from rdf.iter_twoples(_thesaurus_entry)
            else:
                yield (ns.FOAF.isPrimaryTopicOf, rdf.QuotedGraph({_iri: _thesaurus_entry}, focus_iri=_iri))


@trovebrowse.gatherer(ns.FOAF.isPrimaryTopicOf)
def gather_cards_focused_on(focus, *, with_amalgamation: bool):
    _identifier_qs = trove_db.ResourceIdentifier.objects.queryset_for_iris(focus.iris)
    _indexcard_qs = trove_db.Indexcard.objects.filter(focus_identifier_set__in=_identifier_qs)
    if with_amalgamation:
        for _latest_rdf in trove_db.LatestIndexcardRdf.objects.filter(indexcard__in=_indexcard_qs):
            yield from rdf.iter_tripleset(_latest_rdf.as_rdf_tripledict())
    else:
        for _indexcard in _indexcard_qs:
            _card_iri = _indexcard.get_iri()
            yield (ns.FOAF.isPrimaryTopicOf, _card_iri)
            yield (_card_iri, ns.RDF.type, ns.TROVE.Indexcard)


@trovebrowse.gatherer(ns.TROVE.usedAtPath)
def gather_paths_used_at(focus):
    ...  # TODO via elasticsearch aggregation
