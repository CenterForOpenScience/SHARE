import datetime
from unittest import mock

from django.test import TestCase
from primitive_metadata import primitive_rdf as rdf

from share import models as share_db
from tests import factories
from trove import digestive_tract
from trove import models as trove_db


_BLARG = rdf.IriNamespace('https://blarg.example/')


class TestDigestiveTractExpel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.focus_1 = _BLARG.this1
        cls.focus_2 = _BLARG.this2
        cls.raw_1, cls.indexcard_1 = _setup_ingested(cls.focus_1)
        cls.raw_2, cls.indexcard_2 = _setup_ingested(cls.focus_2)
        cls.raw_supp = _setup_supplementary(cls.focus_1, cls.raw_1.suid, cls.indexcard_1)

    def setUp(self):
        super().setUp()
        self.notified_indexcard_ids = set()
        self.enterContext(mock.patch(
            'share.search.index_messenger.IndexMessenger.notify_indexcard_update',
            new=self._replacement_notify_indexcard_update,
        ))
        self.mock_derive_task = self.enterContext(mock.patch('trove.digestive_tract.task__derive'))

    def _replacement_notify_indexcard_update(self, indexcards, **kwargs):
        self.notified_indexcard_ids.update(_card.id for _card in indexcards)

    def enterContext(self, context_manager):
        # TestCase.enterContext added in python3.11 -- implementing here until then
        result = context_manager.__enter__()
        self.addCleanup(lambda: context_manager.__exit__(None, None, None))
        return result

    def test_setup(self):
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertEqual(share_db.RawDatum.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_rdf)
        self.assertIsNotNone(self.indexcard_2.latest_rdf)
        self.assertEqual(self.indexcard_1.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.supplementary_rdf_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # neither notified indexes nor enqueued re-derive
        self.assertEqual(self.notified_indexcard_ids, set())
        self.mock_derive_task.delay.assert_not_called()

    def test_expel(self):
        with mock.patch('trove.digestive_tract.expel_suid') as _mock_expel_suid:
            _user = self.raw_1.suid.source_config.source.user
            digestive_tract.expel(from_user=_user, record_identifier=self.raw_1.suid.identifier)
        _mock_expel_suid.assert_called_once_with(self.raw_1.suid)

    def test_expel_suid(self):
        digestive_tract.expel_suid(self.raw_1.suid)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNotNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertEqual(share_db.RawDatum.objects.count(), 3)
        with self.assertRaises(trove_db.LatestIndexcardRdf.DoesNotExist):
            self.indexcard_1.latest_rdf  # deleted
        self.assertIsNotNone(self.indexcard_2.latest_rdf)
        self.assertEqual(self.indexcard_1.archived_rdf_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_2.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_rdf_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_2.supplementary_rdf_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # notified indexes of update; did not enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, {self.indexcard_1.id})
        self.mock_derive_task.delay.assert_not_called()

    def test_expel_supplementary_suid(self):
        digestive_tract.expel_suid(self.raw_supp.suid)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertEqual(share_db.RawDatum.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_rdf)
        self.assertIsNotNone(self.indexcard_2.latest_rdf)
        self.assertEqual(self.indexcard_1.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_rdf_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.supplementary_rdf_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # did not notify indexes of update; did enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, set())
        self.mock_derive_task.delay.assert_called_once_with(self.indexcard_1.id)

    def test_expel_expired_task(self):
        with mock.patch('trove.digestive_tract.expel_expired_data') as _mock_expel_expired:
            digestive_tract.task__expel_expired_data.apply()
        _mock_expel_expired.assert_called_once_with(datetime.date.today())

    def test_expel_expired(self):
        _today = datetime.date.today()
        self.raw_2.expiration_date = _today
        self.raw_2.save()
        digestive_tract.expel_expired_data(_today)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNotNone(self.indexcard_2.deleted)  # marked deleted
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertEqual(share_db.RawDatum.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_rdf)
        with self.assertRaises(trove_db.LatestIndexcardRdf.DoesNotExist):
            self.indexcard_2.latest_rdf  # deleted
        self.assertEqual(self.indexcard_1.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_rdf_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_1.supplementary_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.supplementary_rdf_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 0)  # deleted
        # notified indexes of update; did not enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, {self.indexcard_2.id})
        self.mock_derive_task.delay.assert_not_called()

    def test_expel_expired_supplement(self):
        _today = datetime.date.today()
        self.raw_supp.expiration_date = _today
        self.raw_supp.save()
        digestive_tract.expel_expired_data(_today)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertEqual(share_db.RawDatum.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_rdf)
        self.assertIsNotNone(self.indexcard_2.latest_rdf)
        self.assertEqual(self.indexcard_1.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_rdf_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_rdf_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.supplementary_rdf_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # did not notify indexes of update; did enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, set())
        self.mock_derive_task.delay.assert_called_once_with(self.indexcard_1.id)


def _setup_ingested(focus_iri: str):
    _focus_ident = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(focus_iri)
    _suid = factories.SourceUniqueIdentifierFactory(
        focus_identifier=_focus_ident,
    )
    _raw = factories.RawDatumFactory(suid=_suid)
    _indexcard = trove_db.Indexcard.objects.create(source_record_suid=_raw.suid)
    _indexcard.focus_identifier_set.add(_focus_ident)
    _latest_rdf = trove_db.LatestIndexcardRdf.objects.create(
        indexcard=_indexcard,
        from_raw_datum=_raw,
        focus_iri=focus_iri,
        rdf_as_turtle='...',
    )
    trove_db.ArchivedIndexcardRdf.objects.create(
        indexcard=_indexcard,
        from_raw_datum=_raw,
        focus_iri=focus_iri,
        rdf_as_turtle=_latest_rdf.rdf_as_turtle,
    )
    _deriver_iri = _BLARG.deriver
    _deriver_ident = trove_db.ResourceIdentifier.objects.get_or_create_for_iri(_deriver_iri)
    trove_db.DerivedIndexcard.objects.create(
        upriver_indexcard=_indexcard,
        deriver_identifier=_deriver_ident,
        derived_checksum_iri='...',
        derived_text='...',
    )
    return _raw, _indexcard


def _setup_supplementary(focus_iri, main_suid, indexcard):
    _supp_suid = factories.SourceUniqueIdentifierFactory(
        focus_identifier=main_suid.focus_identifier,
        source_config=main_suid.source_config,
        is_supplementary=True,
    )
    _supp_raw = factories.RawDatumFactory(suid=_supp_suid)
    trove_db.SupplementaryIndexcardRdf.objects.create(
        indexcard=indexcard,
        from_raw_datum=_supp_raw,
        supplementary_suid=_supp_suid,
        focus_iri=focus_iri,
        rdf_as_turtle='...',
    )
    return _supp_raw
