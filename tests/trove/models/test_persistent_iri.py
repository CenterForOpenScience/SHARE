from django.db import IntegrityError
from django.test import TestCase
import gather

from trove.models import PersistentIri


class TestPersistentIri(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.iri_with_authority = 'foo://wibbleplop.example/la'
        cls.iri_without_authority = 'ha:ba:pow'
        cls.piri_foo = PersistentIri.objects.create(
            sufficiently_unique_iri='://wibbleplop.example/la',
            scheme_list=['foo', 'bla'],
        )
        cls.piri_ha = PersistentIri.objects.create(
            sufficiently_unique_iri='ha:ba:pow',
            scheme_list=['ha'],
        )

    def test_scheme_equivalence_with_authority(self):
        self.assertEqual(self.piri_foo.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(self.piri_foo.scheme_list, ['foo', 'bla'])
        self.assertEqual(self.piri_foo.build_iri(), 'foo://wibbleplop.example/la')
        for _iri in ('foo://wibbleplop.example/la', 'blarg://wibbleplop.example/la'):
            self.assertTrue(self.piri_foo.equivalent_to_iri(_iri))
        _bar_iri = 'bar://wibbleplop.example/la'
        _piri_foo = PersistentIri.objects.get_for_iri(_bar_iri)
        self.assertEqual(_piri_foo.id, self.piri_foo.id)
        self.assertEqual(_piri_foo.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_piri_foo.scheme_list, ['foo', 'bla'])
        self.assertEqual(_piri_foo.build_iri(), 'foo://wibbleplop.example/la')
        _piri_bar = PersistentIri.objects.get_or_create_for_iri(_bar_iri)
        self.assertEqual(_piri_bar.id, self.piri_foo.id)
        self.assertEqual(_piri_bar.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_piri_bar.scheme_list, ['foo', 'bla', 'bar'])
        self.assertEqual(_piri_bar.build_iri(), 'foo://wibbleplop.example/la')
        _http_iri = 'http://wibbleplop.example/la'
        _piri_http = PersistentIri.objects.get_or_create_for_iri(_http_iri)
        self.assertEqual(_piri_http.id, self.piri_foo.id)
        self.assertEqual(_piri_http.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_piri_http.scheme_list, ['foo', 'bla', 'bar', 'http'])
        self.assertEqual(_piri_http.build_iri(), 'http://wibbleplop.example/la')
        _https_iri = 'https://wibbleplop.example/la'
        _piri_https = PersistentIri.objects.get_or_create_for_iri(_https_iri)
        self.assertEqual(_piri_https.id, self.piri_foo.id)
        self.assertEqual(_piri_https.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_piri_https.scheme_list, ['foo', 'bla', 'bar', 'http', 'https'])
        self.assertEqual(_piri_https.build_iri(), 'https://wibbleplop.example/la')

    def test_equivalence_without_authority(self):
        _piri = PersistentIri.objects.get_for_iri('ha:ba:pow')
        self.assertEqual(_piri.id, self.piri_ha.id)
        self.assertEqual(_piri.sufficiently_unique_iri, 'ha:ba:pow')
        self.assertEqual(_piri.scheme_list, ['ha'])
        self.assertEqual(_piri.build_iri(), 'ha:ba:pow')
        self.assertTrue(_piri.equivalent_to_iri('ha:ba:pow'))
        self.assertFalse(_piri.equivalent_to_iri('ma:ba:pow'))
        with self.assertRaises(PersistentIri.DoesNotExist):
            PersistentIri.objects.get_for_iri('wa:ba:pow')

    def test_check_a(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri='//goodbye.example',  # missing :
                scheme_list=['hello'],
            )

    def test_check_b(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri='good:bye',
                scheme_list=['merp'],  # mismatch
            )

    def test_check_c(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri='hello:goodbye',
                scheme_list=['hello', 'toomuch'],  # extra scheme
            )

    def test_check_d(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri='://goodbye',
                scheme_list=[],  # empty
            )

    def test_check_e(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri=':goodbye',  # missing // (or scheme)
                scheme_list=['hello'],
            )

    def test_check_f(self):
        with self.assertRaises(IntegrityError):
            PersistentIri.objects.create(
                sufficiently_unique_iri='hello:goodbye',
                scheme_list=[],  # empty
            )

    def test_find_equivalent(self):
        _cases_with_authority = [
            # (expected, tripledict)
            ('foo://wibbleplop.example/la', {
                'blerp:blop': {},
                'foo://wibbleplop.example/la': {},
            }),
            ('blaz://wibbleplop.example/la', {
                'blaz://wibbleplop.example/la': {},
            }),
            ('blarg:blerg', {
                'blog:blig': {
                    gather.OWL.sameAs: {'blip://blop.example/blig'},
                },
                'blarg:blerg': {
                    gather.OWL.sameAs: {'blip://blop.example/blep', 'bir://wibbleplop.example/la'},
                },
            }),
            ('blarg:blerg', {
                'blog:blig': {
                    gather.OWL.sameAs: {'blip://blop.example/blig'},
                },
                'blarg:blerg': {
                    gather.OWL.sameAs: {'blip://blop.example/blep', 'bip://wibbleplop.example/la'},
                },
            }),
        ]
        for _expected_equivalent, _tripledict in _cases_with_authority:
            self.assertEqual(self.piri_foo.find_equivalent_iri(_tripledict), _expected_equivalent)
