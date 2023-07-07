from django.db import IntegrityError
from django.test import TestCase
import gather

from trove.models import ResourceIdentifier


class TestResourceIdentifier(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.iri_with_authority = 'foo://wibbleplop.example/la'
        cls.iri_without_authority = 'ha:ba:pow'
        cls.identifier_foo = ResourceIdentifier.objects.create(
            sufficiently_unique_iri='://wibbleplop.example/la',
            scheme_list=['foo', 'bla'],
        )
        cls.identifier_ha = ResourceIdentifier.objects.create(
            sufficiently_unique_iri='ha:ba:pow',
            scheme_list=['ha'],
        )

    def test_scheme_equivalence_with_authority(self):
        self.assertEqual(self.identifier_foo.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(self.identifier_foo.scheme_list, ['foo', 'bla'])
        self.assertEqual(self.identifier_foo.as_iri(), 'foo://wibbleplop.example/la')
        for _iri in ('foo://wibbleplop.example/la', 'blarg://wibbleplop.example/la'):
            self.assertTrue(self.identifier_foo.equivalent_to_iri(_iri))
        _bar_iri = 'bar://wibbleplop.example/la'
        _identifier_foo = ResourceIdentifier.objects.get_for_iri(_bar_iri)
        self.assertEqual(_identifier_foo.id, self.identifier_foo.id)
        self.assertEqual(_identifier_foo.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_identifier_foo.scheme_list, ['foo', 'bla'])
        self.assertEqual(_identifier_foo.as_iri(), 'foo://wibbleplop.example/la')
        _identifier_bar = ResourceIdentifier.objects.get_or_create_for_iri(_bar_iri)
        self.assertEqual(_identifier_bar.id, self.identifier_foo.id)
        self.assertEqual(_identifier_bar.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_identifier_bar.scheme_list, ['foo', 'bla', 'bar'])
        self.assertEqual(_identifier_bar.as_iri(), 'foo://wibbleplop.example/la')
        _http_iri = 'http://wibbleplop.example/la'
        _identifier_http = ResourceIdentifier.objects.get_or_create_for_iri(_http_iri)
        self.assertEqual(_identifier_http.id, self.identifier_foo.id)
        self.assertEqual(_identifier_http.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_identifier_http.scheme_list, ['foo', 'bla', 'bar', 'http'])
        self.assertEqual(_identifier_http.as_iri(), 'http://wibbleplop.example/la')
        _https_iri = 'https://wibbleplop.example/la'
        _identifier_https = ResourceIdentifier.objects.get_or_create_for_iri(_https_iri)
        self.assertEqual(_identifier_https.id, self.identifier_foo.id)
        self.assertEqual(_identifier_https.sufficiently_unique_iri, '://wibbleplop.example/la')
        self.assertEqual(_identifier_https.scheme_list, ['foo', 'bla', 'bar', 'http', 'https'])
        self.assertEqual(_identifier_https.as_iri(), 'https://wibbleplop.example/la')

    def test_equivalence_without_authority(self):
        _identifier = ResourceIdentifier.objects.get_for_iri('ha:ba:pow')
        self.assertEqual(_identifier.id, self.identifier_ha.id)
        self.assertEqual(_identifier.sufficiently_unique_iri, 'ha:ba:pow')
        self.assertEqual(_identifier.scheme_list, ['ha'])
        self.assertEqual(_identifier.as_iri(), 'ha:ba:pow')
        self.assertTrue(_identifier.equivalent_to_iri('ha:ba:pow'))
        self.assertFalse(_identifier.equivalent_to_iri('ma:ba:pow'))
        with self.assertRaises(ResourceIdentifier.DoesNotExist):
            ResourceIdentifier.objects.get_for_iri('wa:ba:pow')

    def test_check_a(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
                sufficiently_unique_iri='//goodbye.example',  # missing :
                scheme_list=['hello'],
            )

    def test_check_b(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
                sufficiently_unique_iri='good:bye',
                scheme_list=['merp'],  # mismatch
            )

    def test_check_c(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
                sufficiently_unique_iri='hello:goodbye',
                scheme_list=['hello', 'toomuch'],  # extra scheme
            )

    def test_check_d(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
                sufficiently_unique_iri='://goodbye',
                scheme_list=[],  # empty
            )

    def test_check_e(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
                sufficiently_unique_iri=':goodbye',  # missing // (or scheme)
                scheme_list=['hello'],
            )

    def test_check_f(self):
        with self.assertRaises(IntegrityError):
            ResourceIdentifier.objects.create(
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
            self.assertEqual(self.identifier_foo.find_equivalent_iri(_tripledict), _expected_equivalent)
