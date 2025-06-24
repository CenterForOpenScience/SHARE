from collections.abc import Collection
import time
import uuid

from tests import factories

from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove import digestive_tract
from trove.vocab.namespaces import BLARG


__all__ = (
    'create_indexcard',
    'create_supplement',
    'index_indexcards',
    'update_indexcard_content',
)


def create_indexcard(
    focus_iri: str | None = None,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
    deriver_iris: Collection[str] = (),
) -> trove_db.Indexcard:
    _focus_iri = focus_iri or BLARG[str(uuid.uuid4())]
    _focus_ident = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_focus_iri)
    _suid = factories.SourceUniqueIdentifierFactory(
        focus_identifier=_focus_ident,
    )
    _indexcard = trove_db.Indexcard.objects.create(source_record_suid=_suid)
    _indexcard.focus_identifier_set.add(
        trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_focus_iri),
    )
    update_indexcard_content(_indexcard, _focus_iri, rdf_twopledict, rdf_tripledict)
    if deriver_iris:
        digestive_tract.derive(_indexcard, deriver_iris)
    return _indexcard


def update_indexcard_content(
    indexcard: trove_db.Indexcard,
    focus_iri: str | None = None,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
) -> None:
    _focus_iri = focus_iri or indexcard.latest_resource_description.focus_iri
    _card_content = _combined_tripledict(_focus_iri, rdf_twopledict, rdf_tripledict)
    indexcard.update_resource_description(_focus_iri, _card_content)


def create_supplement(
    indexcard: trove_db.Indexcard,
    focus_iri: str,
    rdf_twopledict: rdf.RdfTwopleDictionary | None = None,
    rdf_tripledict: rdf.RdfTripleDictionary | None = None,
) -> trove_db.SupplementaryResourceDescription:
    _main_suid = indexcard.source_record_suid
    _supp_suid = factories.SourceUniqueIdentifierFactory(
        focus_identifier=_main_suid.focus_identifier,
        source_config=_main_suid.source_config,
        is_supplementary=True,
    )
    return indexcard.update_supplementary_description(
        _supp_suid,
        focus_iri,
        _combined_tripledict(focus_iri, rdf_twopledict, rdf_tripledict),
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
    return _graph.tripledict or {
        focus_iri: {
            BLARG.timeNonce: {rdf.literal(time.time_ns())},
        },
    }
