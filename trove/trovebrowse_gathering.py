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
    focustype_iris={ns.RDFS.Resource},
    thesaurus=TROVE_API_THESAURUS,
)


trovebrowse = gather.GatheringOrganizer(
    namestory=(
        rdf.literal('trovebrowse organizer', language='en'),
    ),
    norms=TROVEBROWSE_NORMS,
    gatherer_params={},
)


@trovebrowse.gatherer(focustype_iris={ns.RDFS.Resource})
def gather_thesaurus_entry(focus):
    _thesaurus = static_vocab.combined_thesaurus__suffuniq()
    for _iri in focus.iris:
        _suffuniq_iri = get_sufficiently_unique_iri(_iri)
        _thesaurus_entry = _thesaurus.get(_suffuniq_iri, None)
        if _thesaurus_entry:
            yield from rdf.iter_twoples(_thesaurus_entry)


@trovebrowse.gatherer(ns.DCTERMS.isReferencedBy)
def gather_cards_referencing(focus):
    ...  # TODO via elasticsearch aggregation


@trovebrowse.gatherer(ns.FOAF.primaryTopicOf)
def gather_cards_focused_on(focus):
    _identifier_qs = trove_db.ResourceIdentifier.objects.queryset_for_iris(focus.iris)
    _indexcard_qs = trove_db.Indexcard.objects.filter(focus_identifier_set__in=_identifier_qs)
    for _indexcard in _indexcard_qs:
        yield (ns.FOAF.primaryTopicOf, _indexcard.get_iri())
