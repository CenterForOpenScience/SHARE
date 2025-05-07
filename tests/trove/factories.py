from collections.abc import Collection

from tests import factories

from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove import digestive_tract


__all__ = (
    'create_indexcard',
    'create_supplement',
    'index_indexcards',
    'update_indexcard_content',
)


def create_indexcard(
    focus_iri: str,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
    deriver_iris: Collection[str] = (),
) -> trove_db.Indexcard:
    _suid = factories.SourceUniqueIdentifierFactory()
    _indexcard = trove_db.Indexcard.objects.create(source_record_suid=_suid)
    _indexcard.focus_identifier_set.add(
        trove_db.ResourceIdentifier.objects.get_or_create_for_iri(focus_iri),
    )
    update_indexcard_content(_indexcard, focus_iri, rdf_twopledict, rdf_tripledict)
    if deriver_iris:
        digestive_tract.derive(_indexcard, deriver_iris)
    return _indexcard


def update_indexcard_content(
    indexcard: trove_db.Indexcard,
    focus_iri: str,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
) -> None:
    _card_content = _combined_tripledict(focus_iri, rdf_twopledict, rdf_tripledict)
    _card_content_turtle = rdf.turtle_from_tripledict(_card_content)
    _raw = factories.RawDatumFactory(suid=indexcard.source_record_suid, datum=_card_content_turtle)
    indexcard.focus_identifier_set.add(
        trove_db.ResourceIdentifier.objects.get_or_create_for_iri(focus_iri),
    )
    trove_db.LatestIndexcardRdf.objects.update_or_create(
        indexcard=indexcard,
        defaults={
            'from_raw_datum': _raw,
            'focus_iri': focus_iri,
            'rdf_as_turtle': _card_content_turtle,
            'turtle_checksum_iri': 'foo',  # not enforced
        },
    )


def create_supplement(
    indexcard: trove_db.Indexcard,
    focus_iri: str,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
) -> trove_db.SupplementaryIndexcardRdf:
    _supp_suid = factories.SourceUniqueIdentifierFactory()
    _supp_content = _combined_tripledict(focus_iri, rdf_twopledict, rdf_tripledict)
    _supp_content_turtle = rdf.turtle_from_tripledict(_supp_content)
    _supp_raw = factories.RawDatumFactory(suid=_supp_suid, datum=_supp_content_turtle)
    return trove_db.SupplementaryIndexcardRdf.objects.create(
        from_raw_datum=_supp_raw,
        indexcard=indexcard,
        supplementary_suid=_supp_suid,
        focus_iri=focus_iri,
        rdf_as_turtle=_supp_content_turtle,
        turtle_checksum_iri='sup',  # not enforced
    )


def index_indexcards(index_strategy, indexcards):
    from share.search import messages
    _messages_chunk = messages.MessagesChunk(
        messages.MessageType.UPDATE_INDEXCARD,
        [_indexcard.id for _indexcard in indexcards],
    )
    assert all(
        _response.is_done
        for _response in index_strategy.pls_handle_messages_chunk(_messages_chunk)
    )
    index_strategy.pls_refresh()


def _combined_tripledict(
    focus_iri: str,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
) -> rdf.RdfTripleDictionary:
    _graph = rdf.RdfGraph()
    if rdf_twopledict is not None:
        _graph.add_twopledict(focus_iri, rdf_twopledict)
    if rdf_tripledict is not None:
        _graph.add_tripledict(rdf_tripledict)
    return _graph.tripledict
