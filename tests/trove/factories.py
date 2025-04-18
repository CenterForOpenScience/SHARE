from collections.abc import Collection

from tests import factories

from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove import digestive_tract


def create_indexcard(
    focus_iri: str,
    rdf_tripledict: rdf.RdfTripleDictionary,
    deriver_iris: Collection[str] = (),
) -> trove_db.Indexcard:
    _suid = factories.SourceUniqueIdentifierFactory()
    _indexcard = trove_db.Indexcard.objects.create(source_record_suid=_suid)
    update_indexcard_content(_indexcard, focus_iri, rdf_tripledict)
    if deriver_iris:
        digestive_tract.derive(_indexcard, deriver_iris)
    return _indexcard


def update_indexcard_content(
    indexcard: trove_db.Indexcard,
    focus_iri: str,
    rdf_tripledict: rdf.RdfTripleDictionary,
) -> None:
    _raw = factories.RawDatumFactory(suid=indexcard.source_record_suid)
    trove_db.LatestIndexcardRdf.objects.update_or_create(
        indexcard=indexcard,
        defaults={
            'from_raw_datum': _raw,
            'focus_iri': focus_iri,
            'rdf_as_turtle': rdf.turtle_from_tripledict(rdf_tripledict),
            'turtle_checksum_iri': 'foo',  # not enforced
        },
    )


def create_supplement(
    indexcard: trove_db.Indexcard,
    focus_iri: str,
    rdf_tripledict: rdf.RdfTripleDictionary,
) -> trove_db.SupplementaryIndexcardRdf:
    _supp_suid = factories.SourceUniqueIdentifierFactory()
    _supp_raw = factories.RawDatumFactory(suid=_supp_suid)
    return trove_db.SupplementaryIndexcardRdf.objects.create(
        from_raw_datum=_supp_raw,
        indexcard=indexcard,
        supplementary_suid=_supp_suid,
        focus_iri=focus_iri,
        rdf_as_turtle=rdf.turtle_from_tripledict(rdf_tripledict),
        turtle_checksum_iri='sup',  # not enforced
    )
