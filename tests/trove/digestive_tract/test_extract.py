import datetime
from django.test import TestCase
from primitive_metadata import primitive_rdf as rdf

from tests import factories
from trove import digestive_tract
from trove import exceptions as trove_exceptions
from trove import models as trove_db


_BLARG = rdf.IriNamespace('https://blarg.example/')


class TestDigestiveTractExtract(TestCase):
    @classmethod
    def setUpTestData(cls):
        _focus_ident = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_BLARG.this)
        cls.raw = factories.RawDatumFactory(
            mediatype='text/turtle',
            datum='''@prefix blarg: <https://blarg.example/> .
blarg:this
    a blarg:Thing ;
    blarg:like blarg:that .
''',
            suid__focus_identifier=_focus_ident,
        )
        cls.supplementary_raw = factories.RawDatumFactory(
            mediatype='text/turtle',
            datum='''@prefix blarg: <https://blarg.example/> .
blarg:this blarg:like blarg:another ;
    blarg:unlike blarg:nonthing .
''',
            suid=factories.SourceUniqueIdentifierFactory(
                source_config=cls.raw.suid.source_config,
                focus_identifier=cls.raw.suid.focus_identifier,
                is_supplementary=True,
            ),
        )

    def test_setup(self):
        self.assertEqual(trove_db.Indexcard.objects.all().count(), 0)
        self.assertEqual(trove_db.LatestIndexcardRdf.objects.all().count(), 0)
        self.assertEqual(trove_db.ArchivedIndexcardRdf.objects.all().count(), 0)
        self.assertEqual(trove_db.SupplementaryIndexcardRdf.objects.all().count(), 0)

    def test_extract(self):
        (_indexcard,) = digestive_tract.extract(self.raw)
        self.assertEqual(_indexcard.source_record_suid_id, self.raw.suid_id)
        _focus_idents = list(
            _indexcard.focus_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focus_idents, ['://blarg.example/this'])
        _focustype_idents = list(
            _indexcard.focustype_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focustype_idents, ['://blarg.example/Thing'])
        self.assertEqual(list(_indexcard.supplementary_rdf_set.all()), [])
        _latest_rdf = _indexcard.latest_rdf
        self.assertEqual(_latest_rdf.from_raw_datum_id, self.raw.id)
        self.assertEqual(_latest_rdf.indexcard_id, _indexcard.id)
        self.assertEqual(_latest_rdf.focus_iri, _BLARG.this)
        self.assertEqual(_latest_rdf.as_rdf_tripledict(), {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that},
            },
        })

    def test_extract_supplementary_without_prior(self):
        _cards = digestive_tract.extract(self.supplementary_raw)
        self.assertEqual(_cards, [])
        self.assertEqual(trove_db.Indexcard.objects.all().count(), 0)
        self.assertEqual(trove_db.LatestIndexcardRdf.objects.all().count(), 0)
        self.assertEqual(trove_db.ArchivedIndexcardRdf.objects.all().count(), 0)
        self.assertEqual(trove_db.SupplementaryIndexcardRdf.objects.all().count(), 0)

    def test_extract_supplementary(self):
        (_orig_indexcard,) = digestive_tract.extract(self.raw)
        _orig_timestamp = _orig_indexcard.latest_rdf.modified
        (_indexcard,) = digestive_tract.extract(self.supplementary_raw)
        self.assertEqual(_orig_indexcard.id, _indexcard.id)
        self.assertEqual(_indexcard.source_record_suid_id, self.raw.suid_id)
        (_supp_rdf,) = _indexcard.supplementary_rdf_set.all()
        self.assertEqual(_supp_rdf.from_raw_datum_id, self.supplementary_raw.id)
        self.assertEqual(_supp_rdf.indexcard_id, _indexcard.id)
        self.assertEqual(_supp_rdf.focus_iri, _BLARG.this)
        self.assertEqual(_supp_rdf.as_rdf_tripledict(), {
            _BLARG.this: {
                _BLARG.like: {_BLARG.another},
                _BLARG.unlike: {_BLARG.nonthing},
            },
        })
        self.assertEqual(_indexcard.latest_rdf.modified, _orig_timestamp)

    def test_extract_empty_with_prior(self):
        (_prior_indexcard,) = digestive_tract.extract(self.raw)
        self.assertFalse(self.raw.no_output)
        self.assertIsNone(_prior_indexcard.deleted)
        # add a later raw
        _empty_raw = factories.RawDatumFactory(
            mediatype='text/turtle',
            datum=' ',
            suid=self.raw.suid,
        )
        (_indexcard,) = digestive_tract.extract(_empty_raw)
        self.assertTrue(_empty_raw.no_output)
        self.assertEqual(_indexcard.id, _prior_indexcard.id)
        self.assertIsNotNone(_indexcard.deleted)
        with self.assertRaises(trove_db.LatestIndexcardRdf.DoesNotExist):
            _indexcard.latest_rdf

    def test_extract_empty_without_prior(self):
        _empty_raw = factories.RawDatumFactory(
            mediatype='text/turtle',
            datum=' ',
        )
        _cards = digestive_tract.extract(_empty_raw)
        self.assertEqual(_cards, [])
        self.assertTrue(_empty_raw.no_output)

    def test_extract_empty_supplementary(self):
        (_orig_indexcard,) = digestive_tract.extract(self.raw)
        digestive_tract.extract(self.supplementary_raw)
        self.assertTrue(_orig_indexcard.supplementary_rdf_set.exists())
        _empty_raw = factories.RawDatumFactory(
            mediatype='text/turtle',
            datum='',
            suid=self.supplementary_raw.suid,
        )
        (_indexcard,) = digestive_tract.extract(_empty_raw)
        self.assertEqual(_indexcard.id, _orig_indexcard.id)
        self.assertFalse(_orig_indexcard.supplementary_rdf_set.exists())

    def test_extract_expired(self):
        self.raw.expiration_date = datetime.date.today()
        with self.assertRaises(trove_exceptions.CannotDigestExpiredDatum):
            digestive_tract.extract(self.raw)

    def test_extract_expired_supplement(self):
        self.supplementary_raw.expiration_date = datetime.date.today()
        with self.assertRaises(trove_exceptions.CannotDigestExpiredDatum):
            digestive_tract.extract(self.supplementary_raw)
