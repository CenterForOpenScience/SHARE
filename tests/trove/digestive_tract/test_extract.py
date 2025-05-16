import datetime
from django.test import TestCase
from primitive_metadata import primitive_rdf as rdf

from tests import factories
from trove import digestive_tract
from trove import exceptions as trove_exceptions
from trove import models as trove_db
from trove.vocab import mediatypes
from trove.vocab.namespaces import BLARG as _BLARG


class TestDigestiveTractExtract(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.ShareUserFactory()
        cls.focus_iri = _BLARG.this
        cls.suid = digestive_tract.sniff(from_user=cls.user, focus_iri=cls.focus_iri)
        cls.raw_turtle = '''@prefix blarg: <http://blarg.example/vocab/> .
blarg:this
    a blarg:Thing ;
    blarg:like blarg:that .
'''
        cls.supp_suid = digestive_tract.sniff(
            from_user=cls.user,
            focus_iri=cls.focus_iri,
            record_identifier=f'supp:{cls.focus_iri}',
            is_supplementary=True,
        )
        cls.supp_raw_turtle = '''@prefix blarg: <http://blarg.example/vocab/> .
blarg:this blarg:like blarg:another ;
    blarg:unlike blarg:nonthing .
'''

    def test_setup(self):
        self.assertEqual(trove_db.Indexcard.objects.all().count(), 0)
        self.assertEqual(trove_db.LatestResourceDescription.objects.all().count(), 0)
        self.assertEqual(trove_db.ArchivedResourceDescription.objects.all().count(), 0)
        self.assertEqual(trove_db.SupplementaryResourceDescription.objects.all().count(), 0)

    def test_extract(self):
        (_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.raw_turtle,
        )
        self.assertEqual(_indexcard.source_record_suid_id, self.suid.id)
        _focus_idents = list(
            _indexcard.focus_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focus_idents, ['://blarg.example/vocab/this'])
        _focustype_idents = list(
            _indexcard.focustype_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focustype_idents, ['://blarg.example/vocab/Thing'])
        self.assertEqual(list(_indexcard.supplementary_description_set.all()), [])
        _latest_resource_description = _indexcard.latest_resource_description
        self.assertEqual(_latest_resource_description.indexcard_id, _indexcard.id)
        self.assertEqual(_latest_resource_description.focus_iri, _BLARG.this)
        self.assertEqual(_latest_resource_description.as_rdf_tripledict(), {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that},
            },
        })
        self.assertEqual(_latest_resource_description.as_rdfdoc_with_supplements().tripledict, {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that},
            },
        })

    def test_extract_before_expiration(self):
        _expir = datetime.date.today() + datetime.timedelta(days=3)
        (_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.raw_turtle,
            expiration_date=_expir,
        )
        self.assertEqual(_indexcard.source_record_suid_id, self.suid.id)
        _focus_idents = list(
            _indexcard.focus_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focus_idents, ['://blarg.example/vocab/this'])
        _focustype_idents = list(
            _indexcard.focustype_identifier_set.values_list('sufficiently_unique_iri', flat=True),
        )
        self.assertEqual(_focustype_idents, ['://blarg.example/vocab/Thing'])
        self.assertEqual(list(_indexcard.supplementary_description_set.all()), [])
        _latest_resource_description = _indexcard.latest_resource_description
        self.assertEqual(_latest_resource_description.indexcard_id, _indexcard.id)
        self.assertEqual(_latest_resource_description.focus_iri, _BLARG.this)
        self.assertEqual(_latest_resource_description.as_rdf_tripledict(), {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that},
            },
        })
        self.assertEqual(_latest_resource_description.as_rdfdoc_with_supplements().tripledict, {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that},
            },
        })

    def test_extract_supplementary_without_prior(self):
        _cards = digestive_tract.extract(
            suid=self.supp_suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.supp_raw_turtle,
        )
        self.assertEqual(_cards, [])
        self.assertEqual(trove_db.Indexcard.objects.all().count(), 0)
        self.assertEqual(trove_db.LatestResourceDescription.objects.all().count(), 0)
        self.assertEqual(trove_db.ArchivedResourceDescription.objects.all().count(), 0)
        self.assertEqual(trove_db.SupplementaryResourceDescription.objects.all().count(), 0)

    def test_extract_supplementary(self):
        (_orig_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.raw_turtle,
        )
        _orig_timestamp = _orig_indexcard.latest_resource_description.modified
        (_indexcard,) = digestive_tract.extract(
            suid=self.supp_suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.supp_raw_turtle,
        )
        self.assertEqual(_orig_indexcard.id, _indexcard.id)
        self.assertEqual(_indexcard.source_record_suid_id, self.suid.id)
        (_supp_rdf,) = _indexcard.supplementary_description_set.all()
        self.assertEqual(_supp_rdf.indexcard_id, _indexcard.id)
        self.assertEqual(_supp_rdf.focus_iri, _BLARG.this)
        self.assertEqual(_supp_rdf.as_rdf_tripledict(), {
            _BLARG.this: {
                _BLARG.like: {_BLARG.another},
                _BLARG.unlike: {_BLARG.nonthing},
            },
        })
        self.assertEqual(_indexcard.latest_resource_description.modified, _orig_timestamp)
        self.assertEqual(_indexcard.latest_resource_description.as_rdfdoc_with_supplements().tripledict, {
            _BLARG.this: {
                rdf.RDF.type: {_BLARG.Thing},
                _BLARG.like: {_BLARG.that, _BLARG.another},
                _BLARG.unlike: {_BLARG.nonthing},
            },
        })

    def test_extract_empty_with_prior(self):
        (_prior_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.raw_turtle,
        )
        self.assertIsNone(_prior_indexcard.deleted)
        # extract an empty
        (_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=' ',  # no data
        )
        self.assertEqual(_indexcard.id, _prior_indexcard.id)
        self.assertIsNotNone(_indexcard.deleted)
        with self.assertRaises(trove_db.LatestResourceDescription.DoesNotExist):
            _indexcard.latest_resource_description

    def test_extract_empty_without_prior(self):
        _cards = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=' ',  # no data
        )
        self.assertEqual(_cards, [])

    def test_extract_empty_supplementary(self):
        (_orig_indexcard,) = digestive_tract.extract(
            suid=self.suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.raw_turtle,
        )
        digestive_tract.extract(
            suid=self.supp_suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=self.supp_raw_turtle,
        )
        self.assertTrue(_orig_indexcard.supplementary_description_set.exists())
        (_indexcard,) = digestive_tract.extract(
            suid=self.supp_suid,
            record_mediatype=mediatypes.TURTLE,
            raw_record=' ',  # no data
        )
        self.assertEqual(_indexcard.id, _orig_indexcard.id)
        self.assertFalse(_orig_indexcard.supplementary_description_set.exists())

    def test_extract_after_expiration(self):
        with self.assertRaises(trove_exceptions.CannotDigestExpiredDatum):
            digestive_tract.extract(
                suid=self.suid,
                record_mediatype=mediatypes.TURTLE,
                raw_record=self.raw_turtle,
                expiration_date=datetime.date.today(),
            )

    def test_extract_supp_after_expiration(self):
        with self.assertRaises(trove_exceptions.CannotDigestExpiredDatum):
            digestive_tract.extract(
                suid=self.supp_suid,
                record_mediatype=mediatypes.TURTLE,
                raw_record=self.supp_raw_turtle,
                expiration_date=datetime.date.today(),
            )
