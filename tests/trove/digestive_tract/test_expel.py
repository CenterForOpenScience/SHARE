import datetime
from unittest import mock

from django.test import TestCase

from share import models as share_db
from tests.trove.factories import (
    create_indexcard,
    create_supplement,
)
from trove import digestive_tract
from trove import models as trove_db
from trove.vocab.namespaces import (
    BLARG,
    TROVE,
)


class TestDigestiveTractExpel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.focus_1 = BLARG.this1
        cls.focus_2 = BLARG.this2
        cls.indexcard_1 = create_indexcard(cls.focus_1, deriver_iris=[TROVE['derive/osfmap_json']])
        cls.indexcard_2 = create_indexcard(cls.focus_2, deriver_iris=[TROVE['derive/osfmap_json']])
        cls.suid_1 = cls.indexcard_1.source_record_suid
        cls.suid_2 = cls.indexcard_2.source_record_suid
        cls.supp = create_supplement(cls.indexcard_1, cls.focus_1)
        cls.supp_suid = cls.supp.supplementary_suid

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
        self.assertIsNotNone(self.indexcard_1.latest_resource_description)
        self.assertIsNotNone(self.indexcard_2.latest_resource_description)
        self.assertEqual(self.indexcard_1.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.supplementary_description_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # neither notified indexes nor enqueued re-derive
        self.assertEqual(self.notified_indexcard_ids, set())
        self.mock_derive_task.delay.assert_not_called()

    def test_expel(self):
        with mock.patch('trove.digestive_tract.expel_suid') as _mock_expel_suid:
            _user = self.suid_1.source_config.source.user
            digestive_tract.expel(from_user=_user, record_identifier=self.suid_1.identifier)
        _mock_expel_suid.assert_called_once_with(self.suid_1)

    def test_expel_suid(self):
        digestive_tract.expel_suid(self.suid_1)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNotNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        with self.assertRaises(trove_db.LatestResourceDescription.DoesNotExist):
            self.indexcard_1.latest_resource_description  # deleted
        self.assertIsNotNone(self.indexcard_2.latest_resource_description)
        self.assertEqual(self.indexcard_1.archived_description_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_2.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_description_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_2.supplementary_description_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # notified indexes of update; did not enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, {self.indexcard_1.id})
        self.mock_derive_task.delay.assert_not_called()

    def test_expel_supplementary_suid(self):
        digestive_tract.expel_suid(self.supp_suid)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_resource_description)
        self.assertIsNotNone(self.indexcard_2.latest_resource_description)
        self.assertEqual(self.indexcard_1.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_description_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.supplementary_description_set.count(), 0)
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
        _latest = self.indexcard_2.latest_resource_description
        _latest.expiration_date = _today
        _latest.save()
        digestive_tract.expel_expired_data(_today)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNotNone(self.indexcard_2.deleted)  # marked deleted
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_resource_description)
        with self.assertRaises(trove_db.LatestResourceDescription.DoesNotExist):
            self.indexcard_2.latest_resource_description  # deleted
        self.assertEqual(self.indexcard_1.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_description_set.count(), 1)  # not deleted
        self.assertEqual(self.indexcard_1.supplementary_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.supplementary_description_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 0)  # deleted
        # notified indexes of update; did not enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, {self.indexcard_2.id})
        self.mock_derive_task.delay.assert_not_called()

    def test_expel_expired_supplement(self):
        _today = datetime.date.today()
        self.supp.expiration_date = _today
        self.supp.save()
        digestive_tract.expel_expired_data(_today)
        self.indexcard_1.refresh_from_db()
        self.indexcard_2.refresh_from_db()
        self.assertIsNone(self.indexcard_1.deleted)
        self.assertIsNone(self.indexcard_2.deleted)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.count(), 3)
        self.assertIsNotNone(self.indexcard_1.latest_resource_description)
        self.assertIsNotNone(self.indexcard_2.latest_resource_description)
        self.assertEqual(self.indexcard_1.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_2.archived_description_set.count(), 1)
        self.assertEqual(self.indexcard_1.supplementary_description_set.count(), 0)  # deleted
        self.assertEqual(self.indexcard_2.supplementary_description_set.count(), 0)
        self.assertEqual(self.indexcard_1.derived_indexcard_set.count(), 1)
        self.assertEqual(self.indexcard_2.derived_indexcard_set.count(), 1)
        # did not notify indexes of update; did enqueue re-derive
        self.assertEqual(self.notified_indexcard_ids, set())
        self.mock_derive_task.delay.assert_called_once_with(self.indexcard_1.id)
