import json

from django.test import TestCase

from tests import factories
from trove import digestive_tract
from trove import models as trove_db
from trove.vocab.namespaces import TROVE, BLARG as _BLARG
from trove.util.iris import get_sufficiently_unique_iri


class TestDigestiveTractDerive(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.focus_iri = _BLARG.this
        _focus_ident = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(cls.focus_iri)
        _raw = factories.RawDatumFactory()
        cls.indexcard = trove_db.Indexcard.objects.create(source_record_suid=_raw.suid)
        cls.indexcard.focus_identifier_set.add(_focus_ident)
        cls.latest_rdf = trove_db.LatestIndexcardRdf.objects.create(
            indexcard=cls.indexcard,
            from_raw_datum=_raw,
            focus_iri=cls.focus_iri,
            rdf_as_turtle='''@prefix blarg: <http://blarg.example/vocab/> .
blarg:this
    a blarg:Thing ;
    blarg:like blarg:that .
''',
        )

    def test_derive(self):
        (_derived,) = digestive_tract.derive(self.indexcard, deriver_iris=[TROVE['derive/osfmap_json_full']])
        self.assertEqual(_derived.upriver_indexcard_id, self.indexcard.id)
        self.assertEqual(_derived.deriver_identifier.sufficiently_unique_iri, get_sufficiently_unique_iri(TROVE['derive/osfmap_json_full']))
        self.assertEqual(json.loads(_derived.derived_text), {
            '@id': 'blarg:this',
            'resourceType': [{'@id': 'blarg:Thing'}],
            'blarg:like': [{'@id': 'blarg:that'}],
        })

    def test_derive_with_supplementary(self):
        _supp_raw = factories.RawDatumFactory(
            suid=factories.SourceUniqueIdentifierFactory(is_supplementary=True),
        )
        trove_db.SupplementaryIndexcardRdf.objects.create(
            indexcard=self.indexcard,
            from_raw_datum=_supp_raw,
            supplementary_suid=_supp_raw.suid,
            focus_iri=self.focus_iri,
            rdf_as_turtle='''@prefix blarg: <http://blarg.example/vocab/> .
blarg:this blarg:unlike blarg:nonthing .
''',
        )
        (_derived,) = digestive_tract.derive(self.indexcard, deriver_iris=[TROVE['derive/osfmap_json_full']])
        self.assertEqual(_derived.upriver_indexcard_id, self.indexcard.id)
        self.assertEqual(_derived.deriver_identifier.sufficiently_unique_iri, get_sufficiently_unique_iri(TROVE['derive/osfmap_json_full']))
        self.assertEqual(json.loads(_derived.derived_text), {
            '@id': 'blarg:this',
            'resourceType': [{'@id': 'blarg:Thing'}],
            'blarg:like': [{'@id': 'blarg:that'}],
            'blarg:unlike': [{'@id': 'blarg:nonthing'}],
        })
