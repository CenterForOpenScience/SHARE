from http import HTTPStatus
from unittest import mock
from urllib.parse import urlencode

from django.test import TestCase

from tests import factories


class TestIngest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.ShareUserFactory(is_trusted=True)

    def test_post(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.post(
                '/trove/ingest?' + urlencode({
                    'focus_iri': 'https://foo.example/blarg',
                    'record_identifier': 'blarg',
                }),
                content_type='text/turtle',
                data='turtleturtleturtle',
                HTTP_AUTHORIZATION=self.user.authorization(),
            )
            self.assertEqual(_resp.status_code, HTTPStatus.CREATED)
            _mock_tract.swallow.assert_called_once_with(
                from_user=self.user,
                record='turtleturtleturtle',
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://foo.example/blarg',
                urgent=True,
                is_supplementary=False,
            )

    def test_post_nonurgent(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.post(
                '/trove/ingest?' + urlencode({
                    'focus_iri': 'https://foo.example/blarg',
                    'record_identifier': 'blarg',
                    'nonurgent': '',
                }),
                content_type='text/turtle',
                data='turtleturtleturtle',
                HTTP_AUTHORIZATION=self.user.authorization(),
            )
            self.assertEqual(_resp.status_code, HTTPStatus.CREATED)
            _mock_tract.swallow.assert_called_once_with(
                from_user=self.user,
                record='turtleturtleturtle',
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://foo.example/blarg',
                urgent=False,
                is_supplementary=False,
            )

    def test_post_supplementary(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.post(
                '/trove/ingest?' + urlencode({
                    'focus_iri': 'https://foo.example/blarg',
                    'record_identifier': 'blarg',
                    'is_supplementary': '',
                }),
                content_type='text/turtle',
                data='turtleturtleturtle',
                HTTP_AUTHORIZATION=self.user.authorization(),
            )
            self.assertEqual(_resp.status_code, HTTPStatus.CREATED)
            _mock_tract.swallow.assert_called_once_with(
                from_user=self.user,
                record='turtleturtleturtle',
                record_identifier='blarg',
                record_mediatype='text/turtle',
                focus_iri='https://foo.example/blarg',
                urgent=True,
                is_supplementary=True,
            )

    def test_delete(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.delete(
                '/trove/ingest?record_identifier=blarg',
                HTTP_AUTHORIZATION=self.user.authorization(),
            )
            self.assertEqual(_resp.status_code, HTTPStatus.OK)
            _mock_tract.expel.assert_called_once_with(
                from_user=self.user,
                record_identifier='blarg',
            )

    def test_anonymous_post(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.post(
                '/trove/ingest?' + urlencode({
                    'focus_iri': 'https://foo.example/blarg',
                    'record_identifier': 'blarg',
                    'is_supplementary': '',
                }),
                content_type='text/turtle',
                data='turtleturtleturtle',
            )
        self.assertEqual(_resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(_mock_tract.swallow.called)

    def test_nontrusted_post(self):
        _nontrusted_user = factories.ShareUserFactory()
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.post(
                '/trove/ingest?' + urlencode({
                    'focus_iri': 'https://foo.example/blarg',
                    'record_identifier': 'blarg',
                    'is_supplementary': '',
                }),
                content_type='text/turtle',
                data='turtleturtleturtle',
                HTTP_AUTHORIZATION=_nontrusted_user.authorization(),
            )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)
        self.assertFalse(_mock_tract.swallow.called)

    def test_anonymous_delete(self):
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.delete('/trove/ingest?record_identifier=blarg')
        self.assertEqual(_resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(_mock_tract.expel.called)

    def test_nontrusted_delete(self):
        _nontrusted_user = factories.ShareUserFactory()
        with mock.patch('trove.views.ingest.digestive_tract') as _mock_tract:
            _resp = self.client.delete(
                '/trove/ingest?record_identifier=blarg',
                HTTP_AUTHORIZATION=_nontrusted_user.authorization(),
            )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)
        self.assertFalse(_mock_tract.expel.called)
