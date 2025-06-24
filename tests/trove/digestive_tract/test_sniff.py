from django.test import TestCase

from share import models as share_db
from tests import factories
from trove import digestive_tract
from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import BLARG


class TestDigestiveTractSniff(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.ShareUserFactory()

    def test_setup(self):
        self.assertEqual(share_db.SourceConfig.objects.all().count(), 0)
        self.assertEqual(share_db.SourceUniqueIdentifier.objects.all().count(), 0)

    def test_sniff(self):
        digestive_tract.sniff(
            from_user=self.user,
            record_identifier='blarg',
            focus_iri=BLARG.this,
        )
        (_suid,) = share_db.SourceUniqueIdentifier.objects.all()
        self.assertEqual(_suid.identifier, 'blarg')
        self.assertEqual(_suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/vocab/this')
        self.assertEqual(_suid.source_config.source.user_id, self.user.id)
        self.assertFalse(_suid.is_supplementary)

    def test_sniff_implicit_record_identifier(self):
        digestive_tract.sniff(
            from_user=self.user,
            focus_iri=BLARG.this,
        )
        (_suid,) = share_db.SourceUniqueIdentifier.objects.all()
        self.assertEqual(_suid.identifier, BLARG.this)
        self.assertEqual(_suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/vocab/this')
        self.assertEqual(_suid.source_config.source.user_id, self.user.id)
        self.assertFalse(_suid.is_supplementary)

    def test_sniff_supplementary(self):
        digestive_tract.sniff(
            from_user=self.user,
            record_identifier='blarg',
            focus_iri=BLARG.this,
            is_supplementary=True,
        )
        (_suid,) = share_db.SourceUniqueIdentifier.objects.all()
        self.assertEqual(_suid.identifier, 'blarg')
        self.assertEqual(_suid.focus_identifier.sufficiently_unique_iri, '://blarg.example/vocab/this')
        self.assertEqual(_suid.source_config.source.user_id, self.user.id)
        self.assertTrue(_suid.is_supplementary)

    def test_error_focus_iri(self):
        with self.assertRaises(trove_exceptions.DigestiveError):
            digestive_tract.sniff(from_user=self.user, focus_iri='blam')
        with self.assertRaises(trove_exceptions.DigestiveError):
            digestive_tract.sniff(from_user=self.user, focus_iri='')

    def test_error_missing_record_identifier(self):
        with self.assertRaises(trove_exceptions.DigestiveError):
            digestive_tract.sniff(from_user=self.user, focus_iri=BLARG.foo, is_supplementary=True)

    def test_error_change_focus(self):
        digestive_tract.sniff(
            from_user=self.user,
            record_identifier='foo',
            focus_iri=BLARG.bar,
        )
        with self.assertRaises(trove_exceptions.DigestiveError):
            digestive_tract.sniff(
                from_user=self.user,
                record_identifier='foo',
                focus_iri=BLARG.different,
            )

    def test_error_change_supplementariness(self):
        digestive_tract.sniff(
            from_user=self.user,
            focus_iri=BLARG.foo,
            record_identifier='foo-supp',
            is_supplementary=True,
        )
        with self.assertRaises(trove_exceptions.DigestiveError):
            digestive_tract.sniff(
                from_user=self.user,
                focus_iri=BLARG.foo,
                record_identifier='foo-supp',
            )
