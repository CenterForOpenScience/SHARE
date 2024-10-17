import datetime
from unittest import mock
from django.test import TestCase

from tests import factories
from trove import digestive_tract
from share import models as share_db


class TestDigestiveTractSwallow(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.ShareUserFactory()
        cls.turtle = '''
@prefix blarg: <https://blarg.example/> .
blarg:this
    a blarg:Thing ;
    blarg:like blarg:that .
'''

    def test_setup(self):
        self.assertEqual(share_db.RawDatum.objects.all().count(), 0)

    def test_swallow(self):
        with mock.patch('trove.digestive_tract.task__extract_and_derive') as _mock_task:
            digestive_tract.swallow(
                from_user=self.user,
                record=self.turtle,
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://blarg.example/this',
            )
        (_raw,) = share_db.RawDatum.objects.all()
        self.assertEqual(_raw.datum, self.turtle)
        self.assertEqual(_raw.mediatype, 'text/turtle')
        self.assertIsNone(_raw.expiration_date)
        self.assertEqual(_raw.suid.identifier, 'blarg')
        self.assertEqual(_raw.suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/this')
        self.assertEqual(_raw.suid.source_config.source.user_id, self.user.id)
        self.assertFalse(_raw.suid.is_supplementary)
        _mock_task.delay.assert_called_once_with(_raw.id, urgent=False)

    def test_swallow_urgent(self):
        with mock.patch('trove.digestive_tract.task__extract_and_derive') as _mock_task:
            digestive_tract.swallow(
                from_user=self.user,
                record=self.turtle,
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://blarg.example/this',
                urgent=True
            )
        (_raw,) = share_db.RawDatum.objects.all()
        self.assertEqual(_raw.datum, self.turtle)
        self.assertEqual(_raw.mediatype, 'text/turtle')
        self.assertIsNone(_raw.expiration_date)
        self.assertEqual(_raw.suid.identifier, 'blarg')
        self.assertEqual(_raw.suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/this')
        self.assertEqual(_raw.suid.source_config.source.user_id, self.user.id)
        self.assertFalse(_raw.suid.is_supplementary)
        _mock_task.delay.assert_called_once_with(_raw.id, urgent=True)

    def test_swallow_supplementary(self):
        with mock.patch('trove.digestive_tract.task__extract_and_derive') as _mock_task:
            digestive_tract.swallow(
                from_user=self.user,
                record=self.turtle,
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://blarg.example/this',
                is_supplementary=True,
            )
        (_raw,) = share_db.RawDatum.objects.all()
        self.assertEqual(_raw.datum, self.turtle)
        self.assertEqual(_raw.mediatype, 'text/turtle')
        self.assertIsNone(_raw.expiration_date)
        self.assertEqual(_raw.suid.identifier, 'blarg')
        self.assertEqual(_raw.suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/this')
        self.assertEqual(_raw.suid.source_config.source.user_id, self.user.id)
        self.assertTrue(_raw.suid.is_supplementary)
        _mock_task.delay.assert_called_once_with(_raw.id, urgent=False)

    def test_swallow_with_expiration(self):
        with mock.patch('trove.digestive_tract.task__extract_and_derive') as _mock_task:
            digestive_tract.swallow(
                from_user=self.user,
                record=self.turtle,
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://blarg.example/this',
                expiration_date=datetime.date(2048, 1, 3),
            )
        (_raw,) = share_db.RawDatum.objects.all()
        self.assertEqual(_raw.datum, self.turtle)
        self.assertEqual(_raw.mediatype, 'text/turtle')
        self.assertEqual(_raw.expiration_date, datetime.date(2048, 1, 3))
        self.assertEqual(_raw.suid.identifier, 'blarg')
        self.assertEqual(_raw.suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/this')
        self.assertEqual(_raw.suid.source_config.source.user_id, self.user.id)
        self.assertFalse(_raw.suid.is_supplementary)
        _mock_task.delay.assert_called_once_with(_raw.id, urgent=False)

    def test_swallow_supplementary_with_expiration(self):
        with mock.patch('trove.digestive_tract.task__extract_and_derive') as _mock_task:
            digestive_tract.swallow(
                from_user=self.user,
                record=self.turtle,
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://blarg.example/this',
                is_supplementary=True,
                expiration_date=datetime.date(2047, 1, 3),
            )
        (_raw,) = share_db.RawDatum.objects.all()
        self.assertEqual(_raw.datum, self.turtle)
        self.assertEqual(_raw.mediatype, 'text/turtle')
        self.assertEqual(_raw.expiration_date, datetime.date(2047, 1, 3))
        self.assertEqual(_raw.suid.identifier, 'blarg')
        self.assertEqual(_raw.suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/this')
        self.assertEqual(_raw.suid.source_config.source.user_id, self.user.id)
        self.assertTrue(_raw.suid.is_supplementary)
        _mock_task.delay.assert_called_once_with(_raw.id, urgent=False)
